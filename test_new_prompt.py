"""
Тест нового промпта для более развернутых ответов
"""

import sys
from pathlib import Path
import asyncio
import yaml

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent))

from src.llm_manager import OpenRouterClient
from src.database import Database

def load_config():
    """Загрузка конфигурации"""
    config_path = Path("config/llm_config.yaml")
    api_keys_path = Path("config/api_keys.yaml")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    with open(api_keys_path, 'r', encoding='utf-8') as f:
        api_keys = yaml.safe_load(f)
    
    config['openrouter'] = {
        'api_key': api_keys['openrouter_api_key'],
        'base_url': 'https://openrouter.ai/api/v1'
    }
    
    return config

async def test_prompt():
    """Тестирование нового промпта"""
    print("\n" + "="*70)
    print("ТЕСТ НОВОГО ПРОМПТА - РАЗВЕРНУТЫЕ ОТВЕТЫ")
    print("="*70 + "\n")
    
    config = load_config()
    
    # Инициализация клиента
    llm_client = OpenRouterClient(
        api_key=config['openrouter']['api_key'],
        base_url=config['openrouter']['base_url']
    )
    
    # Загружаем данные из БД
    db = Database('data/stocks.db')
    
    # Берем AMD как пример (падает на -3.94%)
    db.cursor.execute("""
        SELECT s.price, s.change_percent, s.volume
        FROM stocks s
        JOIN companies c ON s.company_id = c.id
        WHERE c.ticker = 'AMD'
        ORDER BY s.analysis_date DESC
        LIMIT 1
    """)
    
    row = db.cursor.fetchone()
    
    if not row:
        print("❌ Данных по AMD нет в БД")
        return
    
    # Подготовка данных для промпта
    stock_data = {
        'ticker': 'AMD',
        'price': row['price'],
        'change': row['change_percent'],
        'volume': row['volume'],
        'additional_info': ''
    }
    
    print(f"📊 Исходные данные:")
    print(f"   Тикер: AMD")
    print(f"   Цена: ${stock_data['price']}")
    print(f"   Изменение: {stock_data['change']:+.2f}%")
    print(f"   Объем: {stock_data['volume']:,}")
    print("\n" + "-"*70 + "\n")
    
    # Тестируем только одну модель (Claude)
    model = config['models'][1]  # Claude 3.5 Sonnet
    
    print(f"🤖 Тестируем модель: {model['name']}")
    print("="*70 + "\n")
    
    try:
        # Формируем промпт
        user_prompt = config['prompt_template'].format(
            ticker=stock_data['ticker'],
            price=stock_data['price'],
            change=stock_data['change'],
            volume=stock_data['volume'],
            additional_info=stock_data['additional_info'] or 'Нет'
        )
        
        response = await llm_client.analyze_async(
            model_id=model['id'],
            model_name=model['name'],
            system_prompt=config['system_prompt'],
            user_prompt=user_prompt,
            temperature=model.get('temperature', 0.3),
            max_tokens=model.get('max_tokens', 1500)
        )
        
        print("📝 ОТВЕТ МОДЕЛИ:")
        print("-"*70)
        print(response['raw_response'])
        print("-"*70)
        print(f"\n✅ Использовано токенов: {response.get('tokens_used', 'N/A')}")
        print(f"📏 Длина ответа: {len(response['raw_response'])} символов")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    
    print("\n" + "="*70)
    print("💡 ОЦЕНКА:")
    print("="*70)
    print("""
Хороший ответ должен содержать:
✓ Конкретные цифры из данных (цена $242.11, изменение -3.94%)
✓ Развернутое объяснение (4-6 предложений)
✓ Интерпретацию для инвестора
✓ Анализ технических показателей
✓ Понятный язык

Плохой ответ:
✗ Общие фразы без конкретики
✗ 1-2 предложения
✗ Придуманные новости
✗ Только сухие факты без объяснений
    """)
    
    db.conn.close()

if __name__ == "__main__":
    try:
        asyncio.run(test_prompt())
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
