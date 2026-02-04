"""
Полный тест анализа с реальными данными
"""

import asyncio
import yaml
import sys
import logging
from pathlib import Path
from datetime import date

# Исправление кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.database import Database
from src.llm_manager import OpenRouterClient
from src.company_info import CompanyInfoProvider
from src.analyzer import StockAnalyzer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def load_config():
    """Загрузка конфигурации"""
    config_dir = Path("config")
    
    # API ключи
    with open(config_dir / "api_keys.yaml", 'r', encoding='utf-8') as f:
        api_keys = yaml.safe_load(f)
    
    # LLM конфигурация
    with open(config_dir / "llm_config.yaml", 'r', encoding='utf-8') as f:
        llm_config = yaml.safe_load(f)
    
    config = llm_config
    config['openrouter'] = {
        'api_key': api_keys.get('openrouter_api_key', ''),
        'base_url': 'https://openrouter.ai/api/v1'
    }
    
    return config


async def main():
    """Главная функция"""
    print("\n" + "="*80)
    print("🧪 ПОЛНЫЙ ТЕСТ АНАЛИЗА")
    print("="*80)
    
    # Загрузка конфигурации
    config = load_config()
    
    # Инициализация компонентов
    print("\n📦 Инициализация компонентов...")
    
    llm_client = OpenRouterClient(
        api_key=config['openrouter']['api_key'],
        base_url=config['openrouter']['base_url']
    )
    
    db = Database(config['database']['path'])
    print(f"   ✅ База данных: {config['database']['path']}")
    
    company_provider = CompanyInfoProvider(
        cache_duration_days=config['company_info']['cache_duration_days'],
        fallback_llm_client=llm_client if config['company_info']['fallback_to_llm'] else None
    )
    print("   ✅ Провайдер информации о компаниях")
    
    analyzer = StockAnalyzer(
        llm_client=llm_client,
        database=db,
        company_provider=company_provider,
        config=config
    )
    print("   ✅ Анализатор")
    
    # Тестовая акция
    test_stock = {
        'ticker': 'NVDA',
        'price': 180.34,
        'change': -4.34,
        'volume': 203_461_100,
        'additional_info': 'NVIDIA - производитель графических процессоров'
    }
    
    print(f"\n📊 ТЕСТОВАЯ АКЦИЯ:")
    print(f"   Тикер: {test_stock['ticker']}")
    print(f"   Цена: ${test_stock['price']}")
    print(f"   Изменение: {test_stock['change']}%")
    print(f"   Объем: {test_stock['volume']:,}")
    
    # Запуск анализа
    print(f"\n🚀 Запуск анализа...")
    
    results = await analyzer.analyze_stocks(
        stocks=[test_stock],
        analysis_date=date.today()
    )
    
    print(f"\n✅ Анализ завершен!")
    print(f"   Успешно: {results['successful']}")
    print(f"   Ошибок: {results['failed']}")
    
    # Проверка результатов в БД
    print(f"\n📚 Проверка данных в БД...")
    
    db_results = db.get_analysis_results(
        analysis_date=date.today(),
        ticker=test_stock['ticker']
    )
    
    print(f"   Найдено записей: {len(db_results)}")
    
    for result in db_results:
        print(f"\n   🤖 Модель: {result['model_name']}")
        print(f"      Прогноз: {result['prediction']}")
        print(f"      Уверенность: {result['confidence']}")
        print(f"      Токенов: {result['tokens_used']}")
        
        # Проверка парсинга
        analysis_text = result.get('analysis_text', '')
        key_factors = result.get('key_factors', [])
        
        if analysis_text:
            print(f"      ✅ Анализ: {len(analysis_text)} символов")
            print(f"         Начало: {analysis_text[:100]}...")
        else:
            print(f"      ❌ Анализ: НЕ НАЙДЕН")
        
        if key_factors:
            print(f"      ✅ Факторов: {len(key_factors)}")
            for i, factor in enumerate(key_factors, 1):
                print(f"         {i}. {factor[:80]}...")
        else:
            print(f"      ❌ Факторы: НЕ НАЙДЕНЫ")
        
        # Валидация
        validation = result.get('validation_flags', {})
        print(f"      Валидация: {validation.get('trust_level', 'UNKNOWN')}")
    
    print("\n" + "="*80)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*80)
    
    db.close()


if __name__ == "__main__":
    asyncio.run(main())
