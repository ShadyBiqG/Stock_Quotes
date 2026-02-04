"""
Модуль для получения котировок акций через Yahoo Finance API
Используется для автоматического получения текущих цен и исторических данных
"""

import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from time import sleep

logger = logging.getLogger(__name__)


class YahooFinanceFetcher:
    """Класс для получения котировок через Yahoo Finance"""
    
    def __init__(self, cache_duration_seconds: int = 300):
        """
        Инициализация фетчера
        
        Args:
            cache_duration_seconds: Длительность кэша в секундах (по умолчанию 5 минут)
        """
        self.cache = {}
        self.cache_duration = cache_duration_seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_current_price(self, ticker: str, retry_count: int = 3) -> Dict:
        """
        Получить текущую цену акции
        
        Args:
            ticker: Тикер акции (например, AAPL)
            retry_count: Количество попыток при ошибке
            
        Returns:
            Словарь с данными: {
                'price': float,
                'change_percent': float,
                'volume': int,
                'source': str,
                'fetched_at': datetime
            }
        """
        # Проверка кэша
        cache_key = f"current_{ticker}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                logger.debug(f"Использование кэшированных данных для {ticker}")
                return cached_data
        
        # Попытка получить данные
        for attempt in range(retry_count):
            try:
                data = self._fetch_from_yahoo(ticker)
                
                if data:
                    # Кэширование результата
                    self.cache[cache_key] = (data, datetime.now())
                    logger.info(f"Получена котировка {ticker}: ${data['price']:.2f}")
                    return data
                
            except Exception as e:
                logger.warning(f"Попытка {attempt + 1}/{retry_count} не удалась для {ticker}: {e}")
                if attempt < retry_count - 1:
                    sleep(1)  # Пауза перед повтором
        
        # Fallback на значения по умолчанию
        logger.warning(f"Не удалось получить данные для {ticker}, используются значения по умолчанию")
        return self._get_default_values(ticker)
    
    def _fetch_from_yahoo(self, ticker: str) -> Optional[Dict]:
        """
        Получение данных напрямую из Yahoo Finance
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Словарь с данными или None при ошибке
        """
        try:
            # Yahoo Finance API v8 (неофициальный, но работает)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            params = {
                'interval': '1d',
                'range': '5d'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Проверка наличия данных
            if 'chart' not in data or 'result' not in data['chart']:
                logger.warning(f"Некорректный ответ от Yahoo Finance для {ticker}")
                return None
            
            result = data['chart']['result'][0]
            
            # Проверка наличия котировок
            if 'meta' not in result or 'indicators' not in result:
                logger.warning(f"Отсутствуют котировки для {ticker}")
                return None
            
            meta = result['meta']
            
            # Текущая цена
            current_price = meta.get('regularMarketPrice')
            if current_price is None:
                logger.warning(f"Отсутствует цена для {ticker}")
                return None
            
            # Предыдущая цена закрытия
            previous_close = meta.get('chartPreviousClose', current_price)
            
            # Расчет изменения в процентах
            if previous_close > 0:
                change_percent = ((current_price - previous_close) / previous_close) * 100
            else:
                change_percent = 0.0
            
            # Объем торгов
            volume = 0
            if 'indicators' in result and 'quote' in result['indicators']:
                quote = result['indicators']['quote'][0]
                volumes = quote.get('volume', [])
                # Берем последний непустой объем
                for v in reversed(volumes):
                    if v is not None:
                        volume = int(v)
                        break
            
            return {
                'price': float(current_price),
                'change_percent': float(change_percent),
                'volume': volume,
                'source': 'yahoo_finance',
                'fetched_at': datetime.now()
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка HTTP запроса для {ticker}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Ошибка парсинга данных для {ticker}: {e}")
            return None
    
    def get_historical_prices(self, ticker: str, days: int = 30) -> List[Dict]:
        """
        Получить исторические цены
        
        Args:
            ticker: Тикер акции
            days: Количество дней истории
            
        Returns:
            Список словарей с историческими данными
        """
        try:
            # Расчет временного диапазона
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Unix timestamps
            period1 = int(start_date.timestamp())
            period2 = int(end_date.timestamp())
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            params = {
                'period1': period1,
                'period2': period2,
                'interval': '1d'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'chart' not in data or 'result' not in data['chart']:
                logger.warning(f"Некорректный ответ от Yahoo Finance для {ticker}")
                return []
            
            result = data['chart']['result'][0]
            
            # Извлечение данных
            timestamps = result.get('timestamp', [])
            indicators = result.get('indicators', {})
            quote = indicators.get('quote', [{}])[0]
            
            closes = quote.get('close', [])
            volumes = quote.get('volume', [])
            
            # Формирование списка
            historical = []
            for i, timestamp in enumerate(timestamps):
                if i < len(closes) and closes[i] is not None:
                    date = datetime.fromtimestamp(timestamp)
                    price = float(closes[i])
                    volume = int(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0
                    
                    # Расчет изменения
                    change_percent = 0.0
                    if i > 0 and closes[i-1] is not None and closes[i-1] > 0:
                        change_percent = ((price - closes[i-1]) / closes[i-1]) * 100
                    
                    historical.append({
                        'date': date,
                        'price': price,
                        'change_percent': change_percent,
                        'volume': volume
                    })
            
            logger.info(f"Получено {len(historical)} исторических записей для {ticker}")
            return historical
            
        except Exception as e:
            logger.error(f"Ошибка получения исторических данных для {ticker}: {e}")
            return []
    
    def _get_default_values(self, ticker: str) -> Dict:
        """
        Получить значения по умолчанию при ошибке
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Словарь с дефолтными значениями
        """
        return {
            'price': 100.0,
            'change_percent': 0.0,
            'volume': 0,
            'source': 'default',
            'fetched_at': datetime.now()
        }
    
    def validate_ticker(self, ticker: str) -> bool:
        """
        Проверить существование тикера
        
        Args:
            ticker: Тикер акции
            
        Returns:
            True если тикер существует, False иначе
        """
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            params = {'interval': '1d', 'range': '1d'}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Проверка наличия результата
            if 'chart' in data and 'result' in data['chart']:
                result = data['chart']['result']
                if result and len(result) > 0 and 'meta' in result[0]:
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Ошибка валидации тикера {ticker}: {e}")
            return False
    
    def clear_cache(self):
        """Очистить кэш"""
        self.cache.clear()
        logger.debug("Кэш очищен")


# Пример использования
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    fetcher = YahooFinanceFetcher()
    
    # Тест получения текущей цены
    tickers = ['AAPL', 'GOOGL', 'MSFT', 'INVALID_TICKER']
    
    for ticker in tickers:
        print(f"\n{'='*60}")
        print(f"Тестирование: {ticker}")
        print('='*60)
        
        # Валидация
        is_valid = fetcher.validate_ticker(ticker)
        print(f"Тикер валиден: {is_valid}")
        
        # Текущая цена
        data = fetcher.get_current_price(ticker)
        print(f"Цена: ${data['price']:.2f}")
        print(f"Изменение: {data['change_percent']:+.2f}%")
        print(f"Объем: {data['volume']:,}")
        print(f"Источник: {data['source']}")
        
        # Исторические данные (только для валидных)
        if is_valid:
            historical = fetcher.get_historical_prices(ticker, days=7)
            if historical:
                print(f"\nИсторические данные (последние 3 дня):")
                for record in historical[-3:]:
                    print(f"  {record['date'].strftime('%Y-%m-%d')}: ${record['price']:.2f} ({record['change_percent']:+.2f}%)")
