"""
Планировщик автоматического запуска анализа по расписанию
"""

import asyncio
import logging
import yaml
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import sys

# Добавление src в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import load_stock_data
from src.database import Database
from src.llm_manager import OpenRouterClient
from src.company_info import CompanyInfoProvider
from src.analyzer import StockAnalyzer
from src.excel_exporter import ExcelExporter


def setup_logging():
    """Настройка логирования"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "scheduler.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def load_config():
    """Загрузка конфигурации из структуры config/"""
    import os
    from pathlib import Path
    
    config_dir = Path("config")
    api_keys_path = config_dir / "api_keys.yaml"
    llm_config_path = config_dir / "llm_config.yaml"
    
    if not api_keys_path.exists() or not llm_config_path.exists():
        raise FileNotFoundError(
            "Конфигурация не найдена! Создайте файлы:\n"
            "  - config/api_keys.yaml\n"
            "  - config/llm_config.yaml"
        )
    
    config = {}
    
    # API ключи
    with open(api_keys_path, 'r', encoding='utf-8') as f:
        api_keys = yaml.safe_load(f)
        config['openrouter'] = {
            'api_key': api_keys.get('openrouter_api_key', ''),
            'base_url': 'https://openrouter.ai/api/v1'
        }
        saved_alphavantage_key = api_keys.get('alphavantage_api_key', '')
    
    # LLM конфигурация
    with open(llm_config_path, 'r', encoding='utf-8') as f:
        llm_config = yaml.safe_load(f)
        saved_api_key = config['openrouter']['api_key']
        saved_base_url = config['openrouter']['base_url']
        
        config.update(llm_config)
        
        if 'openrouter' not in config:
            config['openrouter'] = {}
        config['openrouter']['api_key'] = saved_api_key
        if 'openrouter' in llm_config and 'base_url' in llm_config['openrouter']:
            config['openrouter']['base_url'] = llm_config['openrouter']['base_url']
        else:
            config['openrouter']['base_url'] = saved_base_url
        
        if 'company_info' not in config:
            config['company_info'] = {}
        config['company_info']['alphavantage_api_key'] = saved_alphavantage_key
    
    # Переменные окружения имеют приоритет
    api_key = os.getenv('OPENROUTER_API_KEY')
    if api_key:
        config['openrouter']['api_key'] = api_key
    
    return config


async def run_analysis():
    """Выполнение анализа"""
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("ЗАПУСК АВТОМАТИЧЕСКОГО АНАЛИЗА")
    logger.info("="*60)
    
    try:
        # Загрузка конфигурации
        config = load_config()
        
        # Проверка наличия файла
        excel_file = Path("Stock quotes.xlsx")
        if not excel_file.exists():
            logger.error("Файл Stock quotes.xlsx не найден!")
            return
        
        # Загрузка данных
        logger.info(f"Загрузка данных из {excel_file}")
        stocks = load_stock_data(str(excel_file))
        logger.info(f"Загружено {len(stocks)} акций")
        
        # Инициализация компонентов
        logger.info("Инициализация компонентов...")
        
        llm_client = OpenRouterClient(
            api_key=config['openrouter']['api_key'],
            base_url=config['openrouter']['base_url']
        )
        
        db = Database(config['database']['path'])
        
        alphavantage_key = config['company_info'].get('alphavantage_api_key', '')
        company_provider = CompanyInfoProvider(
            cache_duration_days=config['company_info']['cache_duration_days'],
            fallback_llm_client=llm_client if config['company_info']['fallback_to_llm'] else None,
            alphavantage_api_key=alphavantage_key if alphavantage_key else None
        )
        
        analyzer = StockAnalyzer(
            llm_client=llm_client,
            database=db,
            company_provider=company_provider,
            config=config
        )
        
        # Запуск анализа
        logger.info("Запуск анализа...")
        stats = await analyzer.analyze_stocks(stocks)
        
        logger.info(
            f"Анализ завершен: {stats['successful']} успешно, "
            f"{stats['failed']} ошибок, "
            f"время: {stats['execution_time']:.1f}с"
        )
        
        # Экспорт
        logger.info("Создание отчета...")
        results = db.get_analysis_results()
        
        exporter = ExcelExporter()
        export_path = exporter.export(results)
        
        logger.info(f"Отчет сохранен: {export_path}")
        
        db.close()
        
        logger.info("="*60)
        logger.info("АНАЛИЗ ЗАВЕРШЕН УСПЕШНО")
        logger.info("="*60)
        
    except Exception as e:
        logger.exception("Ошибка выполнения анализа")


def main():
    """Главная функция планировщика"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("ЗАПУСК ПЛАНИРОВЩИКА")
    logger.info("="*60)
    
    # Загрузка конфигурации
    config = load_config()
    
    scheduler_config = config.get('scheduler', {})
    
    if not scheduler_config.get('enabled', False):
        logger.warning("Планировщик отключен в конфигурации!")
        logger.info("Включите планировщик в config/llm_config.yaml: scheduler.enabled = true")
        return
    
    # Создание планировщика
    scheduler = AsyncIOScheduler(
        timezone=scheduler_config.get('timezone', 'Europe/Moscow')
    )
    
    # Добавление задач из конфигурации
    schedules = scheduler_config.get('schedule', [])
    
    if not schedules:
        logger.warning("Нет расписаний в конфигурации!")
        return
    
    for schedule in schedules:
        cron_expr = schedule.get('cron')
        description = schedule.get('description', 'Анализ котировок')
        
        if not cron_expr:
            logger.warning(f"Пропущено расписание без cron: {schedule}")
            continue
        
        # Парсинг cron выражения
        # Формат: минута час день месяц день_недели
        parts = cron_expr.split()
        
        if len(parts) != 5:
            logger.error(f"Некорректное cron выражение: {cron_expr}")
            continue
        
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone=scheduler_config.get('timezone', 'Europe/Moscow')
        )
        
        scheduler.add_job(
            run_analysis,
            trigger=trigger,
            id=f"analysis_{cron_expr}",
            name=description,
            replace_existing=True
        )
        
        logger.info(f"Добавлена задача: {description}")
        logger.info(f"  Расписание: {cron_expr}")
    
    # Запуск планировщика
    scheduler.start()
    
    logger.info("Планировщик запущен")
    logger.info("Нажмите Ctrl+C для остановки")
    
    try:
        # Бесконечный цикл
        asyncio.get_event_loop().run_forever()
    
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка планировщика...")
        scheduler.shutdown()
        logger.info("Планировщик остановлен")


if __name__ == "__main__":
    main()
