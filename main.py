"""
Главный скрипт для анализа котировок акций через CLI
"""

import asyncio
import logging
import yaml
import os
import sys
from pathlib import Path
from datetime import date, datetime

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Добавление src в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import load_stock_data, DataLoader
from src.database import Database
from src.llm_manager import OpenRouterClient
from src.company_info import CompanyInfoProvider
from src.analyzer import StockAnalyzer
from src.excel_exporter import ExcelExporter


def setup_logging(config: dict) -> None:
    """
    Настройка логирования
    
    Args:
        config: Конфигурация
    """
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Создание директории для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Настройка логирования
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(log_dir / "analysis.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def load_config() -> dict:
    """
    Загрузка конфигурации
    
    Returns:
        Словарь с конфигурацией
    """
    config_path = Path("config.yaml")
    
    if not config_path.exists():
        raise FileNotFoundError(
            "Файл config.yaml не найден! "
            "Скопируйте config.yaml.example и настройте параметры."
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Проверка API ключа через переменную окружения
    api_key = os.getenv('OPENROUTER_API_KEY')
    if api_key:
        config['openrouter']['api_key'] = api_key
    
    return config


def print_banner() -> None:
    """Вывод баннера приложения"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║           📊 Stock Quotes Analyzer 📊                        ║
║                                                               ║
║      Анализ котировок через OpenRouter LLM                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_stats(stats: dict, summary: dict) -> None:
    """
    Вывод статистики выполнения
    
    Args:
        stats: Статистика выполнения
        summary: Сводка по результатам
    """
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТЫ АНАЛИЗА")
    print("="*60)
    
    print(f"\n⏱️  Время выполнения: {stats['execution_time']:.1f} секунд")
    print(f"\n✅ Успешно проанализировано: {stats['successful']} акций")
    print(f"❌ Ошибок: {stats['failed']} акций")
    
    if stats['errors']:
        print(f"\n⚠️  Ошибки:")
        for error in stats['errors'][:5]:  # Показать первые 5
            print(f"   • {error['ticker']}: {error['error']}")
        if len(stats['errors']) > 5:
            print(f"   ... и еще {len(stats['errors']) - 5}")
    
    print(f"\n📈 Прогнозы:")
    predictions = summary.get('predictions', {})
    total = summary.get('total_stocks', 0)
    
    if total > 0:
        growing = predictions.get('РАСТЕТ', 0)
        falling = predictions.get('ПАДАЕТ', 0)
        stable = predictions.get('СТАБИЛЬНА', 0)
        
        print(f"   🟢 Растут:     {growing:3d} ({growing/total*100:5.1f}%)")
        print(f"   🔴 Падают:     {falling:3d} ({falling/total*100:5.1f}%)")
        print(f"   🟡 Стабильны:  {stable:3d} ({stable/total*100:5.1f}%)")
    
    consensus_rate = summary.get('consensus_rate', 0)
    print(f"\n🤝 Консенсус моделей: {consensus_rate:.1f}%")
    
    print("\n" + "="*60)


async def main():
    """Главная функция"""
    try:
        # Баннер
        print_banner()
        
        # Загрузка конфигурации
        print("🔧 Загрузка конфигурации...")
        config = load_config()
        
        # Настройка логирования
        setup_logging(config)
        logger = logging.getLogger(__name__)
        logger.info("="*60)
        logger.info("ЗАПУСК АНАЛИЗА КОТИРОВОК")
        logger.info("="*60)
        
        # Поиск Excel файла
        excel_file = "Stock quotes.xlsx"
        if not Path(excel_file).exists():
            print(f"❌ Файл {excel_file} не найден!")
            print("   Поместите файл с котировками в текущую директорию.")
            return
        
        # Инициализация компонентов
        print("\n🔧 Инициализация компонентов...")
        
        # OpenRouter клиент
        try:
            llm_client = OpenRouterClient(
                api_key=config['openrouter']['api_key'],
                base_url=config['openrouter']['base_url']
            )
            print("   ✅ OpenRouter клиент")
        except ValueError as e:
            print(f"   ❌ {e}")
            return
        
        # База данных
        db = Database(config['database']['path'])
        print(f"   ✅ База данных: {config['database']['path']}")
        
        # Загрузка данных (используется БД для получения котировок)
        print(f"\n📂 Загрузка тикеров из {excel_file}...")
        stocks = load_stock_data(excel_file, database=db)
        
        if not stocks:
            print("❌ Не удалось загрузить данные из файла!")
            return
        
        # Статистика загруженных данных
        data_stats = DataLoader.validate_data(stocks)
        print(f"✅ Загружено {data_stats['total']} акций")
        print(f"   • Растут: {data_stats['growing']}")
        print(f"   • Падают: {data_stats['falling']}")
        print(f"   • Стабильны: {data_stats['stable']}")
        
        # Провайдер информации о компаниях
        alphavantage_key = config['company_info'].get('alphavantage_api_key', '')
        company_provider = CompanyInfoProvider(
            cache_duration_days=config['company_info']['cache_duration_days'],
            fallback_llm_client=llm_client if config['company_info']['fallback_to_llm'] else None,
            alphavantage_api_key=alphavantage_key if alphavantage_key else None
        )
        print("   ✅ Провайдер информации о компаниях")
        
        # Анализатор
        analyzer = StockAnalyzer(
            llm_client=llm_client,
            database=db,
            company_provider=company_provider,
            config=config
        )
        print("   ✅ Анализатор")
        
        # Запуск анализа
        print(f"\n🚀 Запуск анализа {len(stocks)} акций...")
        print(f"   Модели: {', '.join([m['name'] for m in config['models']])}")
        print()
        
        analysis_date = date.today()
        stats = await analyzer.analyze_stocks(stocks, analysis_date)
        
        # Получение сводки
        summary = analyzer.get_analysis_summary(analysis_date)
        
        # Вывод статистики
        print_stats(stats, summary)
        
        # Экспорт в Excel
        print("\n📄 Экспорт результатов в Excel...")
        
        results = db.get_analysis_results(analysis_date=analysis_date)
        
        exporter = ExcelExporter()
        export_path = exporter.export(results, analysis_date)
        
        print(f"✅ Отчет сохранен: {export_path}")
        
        # Закрытие БД
        db.close()
        
        print("\n✨ Анализ завершен успешно!")
        logger.info("Анализ завершен успешно")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        logging.info("Прервано пользователем")
    
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logging.exception("Критическая ошибка")
        raise


if __name__ == "__main__":
    # Запуск асинхронной функции
    asyncio.run(main())
