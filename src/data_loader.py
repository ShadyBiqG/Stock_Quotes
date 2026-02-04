"""
Загрузчик данных из Excel файла с котировками акций
Excel файл содержит только список тикеров, данные о котировках берутся из БД

v3.0: Поддержка загрузки из companies.json с автоматическим получением котировок через Yahoo Finance
"""

import pandas as pd
import json
from typing import List, Dict, Optional
import logging
from pathlib import Path
from datetime import date

logger = logging.getLogger(__name__)


class DataLoader:
    """Класс для загрузки и валидации данных из Excel файла или JSON"""
    
    def __init__(self, filepath: str, database=None, price_fetcher=None, config=None):
        """
        Инициализация загрузчика данных
        
        Args:
            filepath: Путь к Excel файлу с тикерами или JSON файлу
            database: Экземпляр Database для загрузки котировок из БД
            price_fetcher: Экземпляр YahooFinanceFetcher для получения котировок (v3.0)
            config: Конфигурация приложения (для настроек обновления котировок)
        """
        self.filepath = Path(filepath)
        self.database = database
        self.price_fetcher = price_fetcher
        self.config = config or {}
        
        # Настройки обновления котировок (v3.0)
        price_updates = self.config.get('price_updates', {})
        self.update_strategy = price_updates.get('strategy', 'daily')
        self.min_update_interval = price_updates.get('min_update_interval_minutes', 15)
        
        if not self.filepath.exists():
            raise FileNotFoundError(f"Файл не найден: {filepath}")
    
    def load(self) -> List[Dict]:
        """
        Загрузка данных из Excel или JSON файла
        
        Returns:
            Список словарей с данными по акциям
        """
        logger.info(f"Загрузка данных из {self.filepath}")
        
        try:
            # v3.0: Определение типа файла
            if self.filepath.suffix.lower() == '.json':
                return self.load_from_companies_json()
            else:
                # Старый формат Excel
                return self.load_from_excel()
            
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            raise
    
    def load_from_excel(self) -> List[Dict]:
        """
        Загрузка данных из Excel файла (legacy)
        
        Returns:
            Список словарей с данными по акциям
        """
        # Чтение Excel файла
        df = pd.read_excel(self.filepath)
        logger.info(f"Загружено {len(df)} строк из Excel")
        
        # Валидация обязательных колонок
        self._validate_columns(df)
        
        # Парсинг и валидация данных
        stocks = self._parse_stocks(df)
        
        logger.info(f"Успешно обработано {len(stocks)} акций")
        return stocks
    
    def load_from_companies_json(self) -> List[Dict]:
        """
        Загрузка списка компаний из JSON файла (v3.0)
        
        Returns:
            Список словарей с данными по акциям
        """
        with open(self.filepath, 'r', encoding='utf-8') as f:
            companies_data = json.load(f)
        
        if 'companies' not in companies_data:
            raise ValueError("JSON файл должен содержать ключ 'companies'")
        
        companies = companies_data['companies']
        logger.info(f"Загружено {len(companies)} компаний из JSON")
        
        stocks = []
        for company in companies:
            ticker = company.get('ticker')
            if not ticker:
                logger.warning("Пропущена компания без тикера")
                continue
            
            # Получить котировку из БД или Yahoo Finance
            stock_data = self._get_or_fetch_stock_data(ticker)
            if stock_data:
                stocks.append(stock_data)
        
        logger.info(f"Успешно обработано {len(stocks)} акций")
        return stocks
    
    def _get_or_fetch_stock_data(self, ticker: str) -> Optional[Dict]:
        """
        Получить данные акции из БД или через Yahoo Finance (v3.0)
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Словарь с данными акции или None
        """
        from datetime import datetime, timedelta
        
        ticker = ticker.strip().upper()
        should_update = False
        
        # Попытка загрузить из БД
        if self.database:
            try:
                self.database.cursor.execute("""
                    SELECT s.price, s.change_percent, s.volume, s.additional_info, 
                           s.analysis_date, s.created_at
                    FROM stocks s
                    JOIN companies c ON s.company_id = c.id
                    WHERE c.ticker = ?
                    ORDER BY s.analysis_date DESC, s.created_at DESC
                    LIMIT 1
                """, (ticker,))
                
                db_row = self.database.cursor.fetchone()
                
                if db_row:
                    # Проверяем, нужно ли обновлять котировку
                    if self.update_strategy == 'cache_only':
                        # Всегда использовать кэш
                        should_update = False
                    elif self.update_strategy == 'always':
                        # Проверяем минимальный интервал
                        created_at_value = db_row['created_at']
                        
                        # SQLite с PARSE_DECLTYPES возвращает datetime напрямую
                        if isinstance(created_at_value, datetime):
                            created_at = created_at_value
                        elif isinstance(created_at_value, str):
                            try:
                                created_at = datetime.fromisoformat(created_at_value)
                            except ValueError:
                                # Если не удалось распарсить, считаем устаревшим
                                should_update = True
                                created_at = None
                        else:
                            should_update = True
                            created_at = None
                        
                        if created_at:
                            time_since_update = datetime.now() - created_at
                            should_update = time_since_update.total_seconds() / 60 >= self.min_update_interval
                    elif self.update_strategy == 'daily':
                        # Обновляем, если дата не сегодняшняя
                        analysis_date_value = db_row['analysis_date']
                        
                        # SQLite с PARSE_DECLTYPES возвращает date напрямую
                        if isinstance(analysis_date_value, date):
                            should_update = analysis_date_value < date.today()
                        elif isinstance(analysis_date_value, str):
                            try:
                                analysis_date = date.fromisoformat(analysis_date_value)
                                should_update = analysis_date < date.today()
                            except ValueError:
                                # Если не удалось распарсить, считаем устаревшим
                                should_update = True
                        else:
                            # Неизвестный тип, обновляем на всякий случай
                            should_update = True
                    
                    if not should_update:
                        stock = {
                            'ticker': ticker,
                            'price': float(db_row['price']) if db_row['price'] else 100.0,
                            'change': float(db_row['change_percent']) if db_row['change_percent'] else 0.0,
                            'volume': int(db_row['volume']) if db_row['volume'] else 0,
                            'additional_info': db_row['additional_info'] or '',
                            'row_index': 0
                        }
                        logger.debug(f"Загружена акция {ticker} из БД (кэш): ${stock['price']}, {stock['change']:+.2f}%")
                        return stock
                    else:
                        logger.info(f"Котировка {ticker} устарела, обновляем через API...")
                    
            except Exception as e:
                logger.warning(f"Ошибка загрузки данных для {ticker} из БД: {e}")
                should_update = True  # Если ошибка чтения - пробуем через API
        
        # Попытка получить через Yahoo Finance
        if self.price_fetcher:
            try:
                logger.info(f"Получение котировки {ticker} через Yahoo Finance...")
                price_data = self.price_fetcher.get_current_price(ticker)
                
                # Сохранение в БД
                if self.database:
                    company_id = self.database.get_or_create_company(ticker)
                    stock_id = self.database.save_stock(
                        ticker=ticker,
                        price=price_data['price'],
                        change=price_data['change_percent'],
                        volume=price_data['volume'],
                        additional_info='',
                        analysis_date=date.today()
                    )
                    # Сохранение источника
                    self.database.save_price_source(stock_id, price_data['source'])
                
                stock = {
                    'ticker': ticker,
                    'price': price_data['price'],
                    'change': price_data['change_percent'],
                    'volume': price_data['volume'],
                    'additional_info': '',
                    'row_index': 0
                }
                logger.info(f"Получена котировка {ticker}: ${stock['price']:.2f}, {stock['change']:+.2f}%")
                return stock
                
            except Exception as e:
                logger.error(f"Ошибка получения котировки для {ticker}: {e}")
        
        # Fallback на значения по умолчанию
        logger.warning(f"Использование значений по умолчанию для {ticker}")
        stock = {
            'ticker': ticker,
            'price': 100.0,
            'change': 0.0,
            'volume': 0,
            'additional_info': '',
            'row_index': 0
        }
        return stock
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Проверка наличия обязательных колонок
        
        Args:
            df: DataFrame с данными
        """
        required_columns = ['Ticker']
        missing = [col for col in required_columns if col not in df.columns]
        
        if missing:
            raise ValueError(
                f"Отсутствуют обязательные колонки: {', '.join(missing)}\n"
                f"Доступные колонки: {', '.join(df.columns)}"
            )
        
        logger.debug("Все обязательные колонки присутствуют")
    
    def _parse_stocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Парсинг данных по акциям
        
        Args:
            df: DataFrame с данными
            
        Returns:
            Список словарей с данными по акциям
        """
        stocks = []
        
        for idx, row in df.iterrows():
            try:
                stock = self._parse_stock_row(row, idx)
                if stock:
                    stocks.append(stock)
            except Exception as e:
                logger.warning(f"Ошибка обработки строки {idx}: {e}")
                continue
        
        return stocks
    
    def _parse_stock_row(self, row: pd.Series, idx: int) -> Optional[Dict]:
        """
        Парсинг одной строки с данными акции
        Данные о котировках берутся из БД, если она подключена
        
        Args:
            row: Строка данных
            idx: Индекс строки
            
        Returns:
            Словарь с данными акции или None если данные некорректны
        """
        # Проверка на пустые значения
        if pd.isna(row['Ticker']):
            logger.warning(f"Строка {idx}: пропущен тикер")
            return None
        
        # Парсинг тикера
        ticker = str(row['Ticker']).strip().upper()
        
        # Если БД подключена, пытаемся получить данные оттуда
        if self.database:
            try:
                # Получаем последнюю котировку из БД
                self.database.cursor.execute("""
                    SELECT s.price, s.change_percent, s.volume, s.additional_info
                    FROM stocks s
                    JOIN companies c ON s.company_id = c.id
                    WHERE c.ticker = ?
                    ORDER BY s.analysis_date DESC, s.created_at DESC
                    LIMIT 1
                """, (ticker,))
                
                db_row = self.database.cursor.fetchone()
                
                if db_row:
                    stock = {
                        'ticker': ticker,
                        'price': float(db_row['price']) if db_row['price'] else 100.0,
                        'change': float(db_row['change_percent']) if db_row['change_percent'] else 0.0,
                        'volume': int(db_row['volume']) if db_row['volume'] else 0,
                        'additional_info': db_row['additional_info'] or '',
                        'row_index': idx
                    }
                    logger.debug(f"Загружена акция {ticker} из БД: ${stock['price']}, {stock['change']:+.2f}%")
                    return stock
                else:
                    # Данных в БД нет - создаем заглушку для первого анализа
                    logger.info(f"Акция {ticker} не найдена в БД, создаем запись с начальными значениями")
                    stock = {
                        'ticker': ticker,
                        'price': 100.0,  # Начальная цена
                        'change': 0.0,
                        'volume': 0,
                        'additional_info': '',
                        'row_index': idx
                    }
                    return stock
                    
            except Exception as e:
                logger.warning(f"Ошибка загрузки данных для {ticker} из БД: {e}")
        
        # Если БД не подключена или старый формат с колонками Price, Change, Volume
        try:
            if 'Price' in row and not pd.isna(row['Price']):
                price = float(row['Price'])
                change = float(row['Change']) if 'Change' in row and not pd.isna(row['Change']) else 0.0
                volume = int(row['Volume']) if 'Volume' in row and not pd.isna(row['Volume']) else 0
                additional_info = str(row['Info']).strip() if 'Info' in row and not pd.isna(row['Info']) else ''
                
                if price <= 0:
                    logger.warning(f"Строка {idx}: некорректная цена {price}")
                    return None
            else:
                # Начальные значения для первого запуска
                price = 100.0
                change = 0.0
                volume = 0
                additional_info = ''
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Строка {idx}: ошибка преобразования типов - {e}")
            # Используем значения по умолчанию
            price = 100.0
            change = 0.0
            volume = 0
            additional_info = ''
        
        stock = {
            'ticker': ticker,
            'price': price,
            'change': change,
            'volume': volume,
            'additional_info': additional_info,
            'row_index': idx
        }
        
        logger.debug(f"Обработана акция: {ticker} (${price}, {change:+.2f}%)")
        return stock
    
    @staticmethod
    def validate_data(stocks: List[Dict]) -> Dict:
        """
        Статистика по загруженным данным
        
        Args:
            stocks: Список данных по акциям
            
        Returns:
            Словарь со статистикой
        """
        if not stocks:
            return {
                'total': 0,
                'growing': 0,
                'falling': 0,
                'stable': 0
            }
        
        total = len(stocks)
        stats = {
            'total': total,
            'growing': sum(1 for s in stocks if s['change'] > 0.5),
            'falling': sum(1 for s in stocks if s['change'] < -0.5),
            'stable': sum(1 for s in stocks if -0.5 <= s['change'] <= 0.5),
            'avg_price': sum(s['price'] for s in stocks) / total if total > 0 else 0,
            'avg_change': sum(s['change'] for s in stocks) / total if total > 0 else 0,
            'tickers': [s['ticker'] for s in stocks]
        }
        
        return stats


def load_stock_data(filepath: str, database=None, price_fetcher=None, config=None) -> List[Dict]:
    """
    Удобная функция для загрузки данных
    
    Args:
        filepath: Путь к Excel файлу с тикерами или JSON файлу (v3.0)
        database: Экземпляр Database для загрузки котировок из БД
        price_fetcher: Экземпляр YahooFinanceFetcher для получения котировок (v3.0)
        config: Конфигурация приложения (для настроек обновления котировок)
        
    Returns:
        Список словарей с данными по акциям
    """
    loader = DataLoader(filepath, database=database, price_fetcher=price_fetcher, config=config)
    return loader.load()


# Пример использования
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Загрузка данных
    try:
        stocks = load_stock_data("data/samples/Stock quotes.xlsx")
        stats = DataLoader.validate_data(stocks)
        
        print(f"\n📊 Статистика загруженных данных:")
        print(f"  Всего акций: {stats['total']}")
        print(f"  Растут: {stats['growing']} ({stats['growing']/stats['total']*100:.1f}%)")
        print(f"  Падают: {stats['falling']} ({stats['falling']/stats['total']*100:.1f}%)")
        print(f"  Стабильны: {stats['stable']} ({stats['stable']/stats['total']*100:.1f}%)")
        print(f"  Средняя цена: ${stats['avg_price']:.2f}")
        print(f"  Среднее изменение: {stats['avg_change']:+.2f}%")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
