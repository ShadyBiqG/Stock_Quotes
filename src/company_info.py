"""
Модуль для получения описания компаний через различные источники:
1. Alphavantage API (бесплатный, требует ключ)
2. Yahoo Finance (через requests, без yfinance)
3. LLM fallback (всегда работает)
"""

import requests
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class CompanyInfoProvider:
    """Класс для получения информации о компаниях"""
    
    def __init__(self, 
                 cache_dir: str = "data/cache",
                 cache_duration_days: int = 30,
                 fallback_llm_client = None,
                 alphavantage_api_key: str = None):
        """
        Инициализация провайдера информации
        
        Args:
            cache_dir: Директория для кэша
            cache_duration_days: Срок действия кэша в днях
            fallback_llm_client: LLM клиент для fallback
            alphavantage_api_key: API ключ Alphavantage (опционально)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_duration = timedelta(days=cache_duration_days)
        self.fallback_llm = fallback_llm_client
        self.alphavantage_key = alphavantage_api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_company_info(self, ticker: str, use_cache: bool = True) -> Dict:
        """
        Получить информацию о компании (использует несколько источников)
        
        Args:
            ticker: Тикер акции
            use_cache: Использовать кэш
            
        Returns:
            Словарь с информацией о компании
        """
        ticker = ticker.upper().strip()
        
        # Проверка кэша
        if use_cache:
            cached = self._get_from_cache(ticker)
            if cached:
                logger.debug(f"Информация о {ticker} получена из кэша")
                return cached
        
        # Попытка 1: Alphavantage API (если есть ключ)
        info = None
        if self.alphavantage_key:
            info = self._get_from_alphavantage(ticker)
            if info and info['name']:
                logger.info(f"Информация о {ticker} получена через Alphavantage")
                self._save_to_cache(ticker, info)
                return info
        
        # Попытка 2: Yahoo Finance через requests (обход yfinance)
        info = self._get_from_yahoo_requests(ticker)
        if info and info['name']:
            logger.info(f"Информация о {ticker} получена через Yahoo Finance")
            self._save_to_cache(ticker, info)
            return info
        
        # Попытка 3: LLM fallback (всегда работает)
        if self.fallback_llm:
            logger.info(f"Используем LLM для получения информации о {ticker}")
            info = self._get_from_llm(ticker)
            if info and info['name']:
                self._save_to_cache(ticker, info)
                return info
        
        # Если ничего не помогло
        logger.warning(f"Не удалось получить информацию о {ticker} из всех источников")
        return self._empty_info(ticker)
    
    def _get_from_alphavantage(self, ticker: str) -> Optional[Dict]:
        """
        Получить данные через Alphavantage API
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Словарь с данными или None
        """
        if not self.alphavantage_key:
            return None
        
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'OVERVIEW',
                'symbol': ticker,
                'apikey': self.alphavantage_key
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Name' in data and data['Name']:
                info = {
                    'ticker': ticker,
                    'name': data.get('Name', ''),
                    'description': data.get('Description', ''),
                    'sector': data.get('Sector', ''),
                    'industry': data.get('Industry', ''),
                    'website': '',
                    'country': data.get('Country', ''),
                    'source': 'alphavantage',
                    'updated_at': datetime.now().isoformat()
                }
                return info
            
            return None
            
        except Exception as e:
            logger.debug(f"Alphavantage не дал данных по {ticker}: {e}")
            return None
    
    def _get_from_yahoo_requests(self, ticker: str) -> Optional[Dict]:
        """
        Получить данные через Yahoo Finance (прямые HTTP запросы)
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Словарь с данными или None
        """
        try:
            # Yahoo Finance Quote Summary
            url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
            params = {
                'modules': 'assetProfile,summaryProfile'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            result = data.get('quoteSummary', {}).get('result', [])
            if not result:
                return None
            
            profile = result[0].get('assetProfile', {})
            summary = result[0].get('summaryProfile', {})
            
            if profile or summary:
                info = {
                    'ticker': ticker,
                    'name': profile.get('longName') or summary.get('longName', ''),
                    'description': profile.get('longBusinessSummary') or summary.get('longBusinessSummary', ''),
                    'sector': profile.get('sector') or summary.get('sector', ''),
                    'industry': profile.get('industry') or summary.get('industry', ''),
                    'website': profile.get('website', ''),
                    'country': profile.get('country', ''),
                    'source': 'yahoo_api',
                    'updated_at': datetime.now().isoformat()
                }
                
                if info['name']:
                    return info
            
            return None
            
        except Exception as e:
            logger.debug(f"Yahoo Finance API не дал данных по {ticker}: {e}")
            return None
    
    def _get_from_llm(self, ticker: str) -> Dict:
        """
        Получить данные через LLM (fallback)
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Словарь с данными
        """
        if not self.fallback_llm:
            return self._empty_info(ticker)
        
        try:
            prompt = f"""
Предоставь краткую информацию о компании с тикером {ticker}.

ВАЖНО:
- Если ты НЕ уверен в информации - напиши "Неизвестно"
- НЕ придумывай данные
- Отвечай кратко и точно

ФОРМАТ ОТВЕТА (только JSON):
{{
    "name": "Название компании",
    "description": "Краткое описание (1-2 предложения)",
    "sector": "Сектор",
    "industry": "Индустрия"
}}

Если компания неизвестна, верни все поля со значением "Неизвестно".
"""
            
            response = self.fallback_llm.query(
                prompt=prompt,
                model_id="openai/gpt-3.5-turbo",
                temperature=0.1
            )
            
            # Парсинг JSON ответа
            data = json.loads(response)
            
            info = {
                'ticker': ticker,
                'name': data.get('name', 'Неизвестно'),
                'description': data.get('description', ''),
                'sector': data.get('sector', ''),
                'industry': data.get('industry', ''),
                'website': '',
                'country': '',
                'source': 'llm_fallback',
                'updated_at': datetime.now().isoformat()
            }
            
            logger.info(f"LLM предоставил информацию о {ticker}")
            return info
            
        except Exception as e:
            logger.error(f"Ошибка получения данных через LLM для {ticker}: {e}")
            return self._empty_info(ticker)
    
    def _empty_info(self, ticker: str) -> Dict:
        """
        Создать пустую запись информации
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Словарь с пустыми данными
        """
        return {
            'ticker': ticker,
            'name': '',
            'description': '',
            'sector': '',
            'industry': '',
            'website': '',
            'country': '',
            'source': 'none',
            'updated_at': datetime.now().isoformat()
        }
    
    def _get_cache_path(self, ticker: str) -> Path:
        """Получить путь к файлу кэша для тикера"""
        return self.cache_dir / f"{ticker}.json"
    
    def _get_from_cache(self, ticker: str) -> Optional[Dict]:
        """
        Получить данные из кэша
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Данные из кэша или None
        """
        cache_file = self._get_cache_path(ticker)
        
        if not cache_file.exists():
            return None
        
        try:
            # Проверка срока действия
            file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - file_time > self.cache_duration:
                logger.debug(f"Кэш для {ticker} устарел")
                return None
            
            # Чтение данных
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            logger.warning(f"Ошибка чтения кэша для {ticker}: {e}")
            return None
    
    def _save_to_cache(self, ticker: str, info: Dict) -> None:
        """
        Сохранить данные в кэш
        
        Args:
            ticker: Тикер акции
            info: Данные для сохранения
        """
        cache_file = self._get_cache_path(ticker)
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Информация о {ticker} сохранена в кэш")
            
        except Exception as e:
            logger.warning(f"Ошибка сохранения кэша для {ticker}: {e}")
    
    def clear_cache(self, ticker: str = None) -> None:
        """
        Очистить кэш
        
        Args:
            ticker: Тикер для очистки (если None - очистить весь кэш)
        """
        if ticker:
            cache_file = self._get_cache_path(ticker)
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Кэш для {ticker} очищен")
        else:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Весь кэш очищен")


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    provider = CompanyInfoProvider()
    
    # Тестирование
    tickers = ['AAPL', 'GOOGL', 'MSFT']
    
    for ticker in tickers:
        info = provider.get_company_info(ticker)
        print(f"\n{ticker}:")
        print(f"  Название: {info['name']}")
        print(f"  Сектор: {info['sector']}")
        print(f"  Источник: {info['source']}")
