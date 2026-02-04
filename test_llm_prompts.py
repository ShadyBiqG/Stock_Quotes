"""
Тестирование промтов и парсинга ответов LLM
"""

import asyncio
import yaml
import logging
import sys
from pathlib import Path

# Исправление кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.llm_manager import OpenRouterClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


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


def print_result(model_name, result):
    """Красивый вывод результата"""
    print("\n" + "="*80)
    print(f"🤖 МОДЕЛЬ: {model_name}")
    print("="*80)
    
    if not result.get('success', False):
        print(f"❌ ОШИБКА: {result.get('error', 'Неизвестная ошибка')}")
        return
    
    print(f"\n📊 ПРОГНОЗ: {result['prediction']}")
    print(f"💪 УВЕРЕННОСТЬ: {result['confidence']}")
    print(f"🎯 ТОКЕНОВ: {result['tokens_used']}")
    
    print("\n📝 АНАЛИЗ:")
    analysis_text = result.get('analysis_text', '')
    if analysis_text:
        print(analysis_text)
    else:
        print("⚠️  Анализ не найден")
    
    print("\n🔑 КЛЮЧЕВЫЕ ФАКТОРЫ:")
    key_factors = result.get('key_factors', [])
    if key_factors:
        for i, factor in enumerate(key_factors, 1):
            print(f"  {i}. {factor}")
    else:
        print("⚠️  Факторы не найдены")
    
    print("\n🚩 ВАЛИДАЦИЯ:")
    validation = result.get('validation_flags', {})
    print(f"  • Формат корректен: {validation.get('format_valid', False)}")
    print(f"  • Уровень доверия: {validation.get('trust_level', 'UNKNOWN')}")
    suspicious = validation.get('suspicious_patterns', [])
    if suspicious:
        print(f"  • Подозрительные паттерны: {', '.join(suspicious)}")
    
    print("\n📄 СЫРОЙ ОТВЕТ:")
    print("-" * 80)
    print(result['raw_response'])
    print("-" * 80)


async def test_single_model(config, model_config, test_stock):
    """Тестирование одной модели"""
    llm_client = OpenRouterClient(
        api_key=config['openrouter']['api_key'],
        base_url=config['openrouter']['base_url']
    )
    
    # Формирование промта
    user_prompt = config['prompt_template'].format(
        ticker=test_stock['ticker'],
        price=test_stock['price'],
        change=test_stock['change'],
        volume=test_stock['volume'],
        additional_info=test_stock.get('additional_info', 'Нет дополнительной информации')
    )
    
    print(f"\n🚀 Запрос к модели: {model_config['name']}")
    print(f"📨 Промт (первые 200 символов):")
    print(user_prompt[:200] + "...")
    
    # Запрос к LLM
    result = await llm_client.analyze_async(
        model_id=model_config['id'],
        model_name=model_config['name'],
        system_prompt=config['system_prompt'],
        user_prompt=user_prompt,
        temperature=model_config.get('temperature', 0.3),
        max_tokens=model_config.get('max_tokens', 1500)
    )
    
    return result


async def main():
    """Главная функция тестирования"""
    print("\n" + "="*80)
    print("🧪 ТЕСТИРОВАНИЕ ПРОМТОВ И ПАРСИНГА LLM")
    print("="*80)
    
    # Загрузка конфигурации
    config = load_config()
    
    # Тестовые данные акции
    test_stock = {
        'ticker': 'AAPL',
        'price': 185.50,
        'change': -2.35,
        'volume': 75_000_000,
        'additional_info': 'Apple Inc. - производитель iPhone, iPad, Mac'
    }
    
    print(f"\n📊 ТЕСТОВАЯ АКЦИЯ:")
    print(f"  Тикер: {test_stock['ticker']}")
    print(f"  Цена: ${test_stock['price']}")
    print(f"  Изменение: {test_stock['change']}%")
    print(f"  Объем: {test_stock['volume']:,}")
    
    # Тестирование каждой модели
    for model_config in config['models']:
        try:
            result = await test_single_model(config, model_config, test_stock)
            print_result(model_config['name'], result)
        except Exception as e:
            print(f"\n❌ ОШИБКА при тестировании {model_config['name']}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
