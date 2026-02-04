"""
Основной движок анализа котировок
Асинхронная обработка с retry механизмом
"""

import logging
import asyncio
from typing import List, Dict
from datetime import date
from tqdm import tqdm
import time

from .llm_manager import OpenRouterClient
from .database import Database
from .company_info import CompanyInfoProvider

logger = logging.getLogger(__name__)


class StockAnalyzer:
    """Класс для анализа котировок акций"""
    
    def __init__(self, 
                 llm_client: OpenRouterClient,
                 database: Database,
                 company_provider: CompanyInfoProvider,
                 config: Dict):
        """
        Инициализация анализатора
        
        Args:
            llm_client: Клиент OpenRouter
            database: База данных
            company_provider: Провайдер информации о компаниях
            config: Конфигурация
        """
        self.llm = llm_client
        self.db = database
        self.company_provider = company_provider
        self.config = config
        
        self.models = config.get('models', [])
        self.system_prompt = config.get('system_prompt', '')
        self.prompt_template = config.get('prompt_template', '')
        
        logger.info("Анализатор инициализирован")
    
    async def analyze_stocks(self, stocks: List[Dict], 
                           analysis_date: date = None,
                           max_retries: int = 3) -> Dict:
        """
        Анализ списка акций
        
        Args:
            stocks: Список данных по акциям
            analysis_date: Дата анализа
            max_retries: Максимум попыток при ошибке
            
        Returns:
            Статистика выполнения
        """
        if analysis_date is None:
            analysis_date = date.today()
        
        logger.info(f"Начало анализа {len(stocks)} акций на {analysis_date}")
        start_time = time.time()
        
        stats = {
            'total': len(stocks),
            'successful': 0,
            'failed': 0,
            'total_tokens': 0,
            'execution_time': 0,
            'errors': []
        }
        
        # Прогресс-бар (ASCII для совместимости с Windows)
        with tqdm(total=len(stocks), desc="Analysis", ascii=True, ncols=80) as pbar:
            for stock in stocks:
                try:
                    await self._analyze_single_stock(
                        stock, 
                        analysis_date, 
                        max_retries
                    )
                    stats['successful'] += 1
                    
                except Exception as e:
                    logger.error(f"Ошибка анализа {stock['ticker']}: {e}")
                    stats['failed'] += 1
                    stats['errors'].append({
                        'ticker': stock['ticker'],
                        'error': str(e)
                    })
                
                finally:
                    pbar.update(1)
                    
                    # Промежуточное сохранение каждые 10 акций
                    if (stats['successful'] + stats['failed']) % 10 == 0:
                        self.db.conn.commit()
                        logger.debug("Промежуточное сохранение в БД")
        
        # Финальное сохранение
        self.db.conn.commit()
        
        stats['execution_time'] = time.time() - start_time
        
        logger.info(
            f"Анализ завершен: {stats['successful']} успешно, "
            f"{stats['failed']} ошибок, "
            f"время: {stats['execution_time']:.1f}с"
        )
        
        return stats
    
    async def _analyze_single_stock(self, 
                                   stock: Dict,
                                   analysis_date: date,
                                   max_retries: int) -> None:
        """
        Анализ одной акции
        
        Args:
            stock: Данные акции
            analysis_date: Дата анализа
            max_retries: Максимум попыток
        """
        ticker = stock['ticker']
        logger.info(f"Анализ {ticker}")
        
        # Получение информации о компании
        company_info = self.company_provider.get_company_info(ticker)
        
        # Сохранение компании и котировки в БД
        stock_id = self.db.save_stock(
            ticker=ticker,
            price=stock['price'],
            change=stock['change'],
            volume=stock['volume'],
            additional_info=stock.get('additional_info', ''),
            analysis_date=analysis_date
        )
        
        # Обновление информации о компании в БД
        if company_info['name']:
            self.db.get_or_create_company(
                ticker=ticker,
                name=company_info['name'],
                description=company_info['description'],
                sector=company_info['sector'],
                industry=company_info['industry']
            )
        
        # Формирование промпта
        user_prompt = self._create_prompt(stock, company_info)
        
        # Запрос ко всем моделям с retry
        results = await self._analyze_with_retry(
            user_prompt,
            max_retries
        )
        
        # Сохранение результатов
        for result in results:
            if result.get('success', False):
                self.db.save_analysis(
                    stock_id=stock_id,
                    model_name=result['model_name'],
                    model_id=result['model_id'],
                    prediction=result['prediction'],
                    reasons=result['reasons'],
                    confidence=result['confidence'],
                    raw_response=result['raw_response'],
                    validation_flags=result['validation_flags'],
                    tokens_used=result['tokens_used'],
                    analysis_text=result.get('analysis_text', ''),
                    key_factors=result.get('key_factors', [])
                )
        
        # Вычисление консенсуса
        consensus = self.llm.calculate_consensus(results)
        
        self.db.save_consensus(
            stock_id=stock_id,
            agreed_prediction=consensus['agreed_prediction'],
            disagreement_count=consensus['disagreement_count'],
            avg_confidence=consensus['avg_confidence']
        )
        
        logger.debug(
            f"{ticker}: консенсус = {consensus['agreed_prediction']}, "
            f"разногласий = {consensus['disagreement_count']}"
        )
    
    def _create_prompt(self, stock: Dict, company_info: Dict) -> str:
        """
        Создать промпт для анализа
        
        Args:
            stock: Данные акции
            company_info: Информация о компании
            
        Returns:
            Сформированный промпт
        """
        # Дополнительная информация
        additional = stock.get('additional_info', '')
        
        if company_info['name']:
            additional = f"{company_info['name']}. {company_info['description']}\n{additional}"
        
        # Форматирование промпта
        prompt = self.prompt_template.format(
            ticker=stock['ticker'],
            price=stock['price'],
            change=stock['change'],
            volume=stock['volume'],
            additional_info=additional or 'Нет дополнительной информации'
        )
        
        return prompt
    
    async def _analyze_with_retry(self, 
                                 user_prompt: str,
                                 max_retries: int) -> List[Dict]:
        """
        Запрос с retry механизмом
        
        Args:
            user_prompt: Промпт пользователя
            max_retries: Максимум попыток
            
        Returns:
            Список результатов от моделей
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                results = await self.llm.analyze_all_async(
                    models=self.models,
                    system_prompt=self.system_prompt,
                    user_prompt=user_prompt
                )
                
                # Проверка на успешные результаты
                successful = [r for r in results if r.get('success', False)]
                
                if successful:
                    return results
                
                logger.warning(f"Попытка {attempt + 1}: нет успешных результатов")
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Попытка {attempt + 1} не удалась: {e}")
                
                # Экспоненциальная задержка
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    logger.info(f"Ожидание {delay}с перед повтором")
                    await asyncio.sleep(delay)
        
        # Все попытки не удались
        logger.error(f"Все {max_retries} попытки не удались")
        
        if last_exception:
            raise last_exception
        
        return []
    
    def get_analysis_summary(self, analysis_date: date = None) -> Dict:
        """
        Получить сводку по анализу
        
        Args:
            analysis_date: Дата анализа
            
        Returns:
            Словарь со сводкой
        """
        if analysis_date is None:
            analysis_date = date.today()
        
        results = self.db.get_analysis_results(analysis_date=analysis_date)
        
        if not results:
            return {
                'date': analysis_date,
                'total_stocks': 0,
                'predictions': {},
                'consensus_rate': 0
            }
        
        # Группировка по тикерам
        stocks_data = {}
        for r in results:
            ticker = r['ticker']
            if ticker not in stocks_data:
                stocks_data[ticker] = {
                    'predictions': [],
                    'price': r['price'],
                    'change': r['change']
                }
            stocks_data[ticker]['predictions'].append(r['prediction'])
        
        # Подсчет прогнозов
        prediction_counts = {'РАСТЕТ': 0, 'ПАДАЕТ': 0, 'СТАБИЛЬНА': 0}
        consensus_count = 0
        
        for ticker, data in stocks_data.items():
            predictions = data['predictions']
            
            # Консенсус = все модели согласны
            if len(set(predictions)) == 1:
                consensus_count += 1
            
            # Большинство голосов
            most_common = max(set(predictions), key=predictions.count)
            prediction_counts[most_common] = prediction_counts.get(most_common, 0) + 1
        
        summary = {
            'date': analysis_date,
            'total_stocks': len(stocks_data),
            'predictions': prediction_counts,
            'consensus_rate': consensus_count / len(stocks_data) * 100 if stocks_data else 0,
            'total_analyses': len(results)
        }
        
        return summary


# Пример использования
if __name__ == "__main__":
    import yaml
    import os
    from pathlib import Path
    from .data_loader import load_stock_data
    
    logging.basicConfig(level=logging.INFO)
    
    # Загрузка конфигурации из структуры config/
    config_dir = Path("../config")
    api_keys_path = config_dir / "api_keys.yaml"
    llm_config_path = config_dir / "llm_config.yaml"
    
    if not api_keys_path.exists() or not llm_config_path.exists():
        raise FileNotFoundError("Конфигурация не найдена! Создайте config/api_keys.yaml и config/llm_config.yaml")
    
    config = {}
    with open(api_keys_path, 'r', encoding='utf-8') as f:
        api_keys = yaml.safe_load(f)
        config['openrouter'] = {
            'api_key': api_keys.get('openrouter_api_key', '') or os.getenv('OPENROUTER_API_KEY', ''),
            'base_url': 'https://openrouter.ai/api/v1'
        }
        saved_alphavantage_key = api_keys.get('alphavantage_api_key', '')
    
    with open(llm_config_path, 'r', encoding='utf-8') as f:
        llm_config = yaml.safe_load(f)
        saved_api_key = config['openrouter']['api_key']
        saved_base_url = config['openrouter']['base_url']
        config.update(llm_config)
        if 'openrouter' not in config:
            config['openrouter'] = {}
        config['openrouter']['api_key'] = saved_api_key
        if 'company_info' not in config:
            config['company_info'] = {}
        config['company_info']['alphavantage_api_key'] = saved_alphavantage_key
    
    # Инициализация компонентов
    llm_client = OpenRouterClient(
        api_key=config['openrouter']['api_key']
    )
    
    db = Database(config['database']['path'])
    company_provider = CompanyInfoProvider()
    
    analyzer = StockAnalyzer(llm_client, db, company_provider, config)
    
    # Загрузка данных
    stocks = load_stock_data("data/samples/Stock quotes.xlsx")
    
    # Запуск анализа
    stats = asyncio.run(analyzer.analyze_stocks(stocks))
    
    print(f"\n📊 Результаты:")
    print(f"  Успешно: {stats['successful']}")
    print(f"  Ошибок: {stats['failed']}")
    print(f"  Время: {stats['execution_time']:.1f}с")
