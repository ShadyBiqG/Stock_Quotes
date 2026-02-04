"""
Проверка API ключа OpenRouter
"""

import sys
from pathlib import Path
import yaml
import requests

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Добавление src в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_api_key():
    """Проверка валидности API ключа OpenRouter"""
    
    print("="*70)
    print("ПРОВЕРКА API КЛЮЧА OPENROUTER")
    print("="*70)
    print()
    
    # Загрузка конфигурации из структуры config/
    import os
    root_dir = Path(__file__).parent.parent
    api_keys_path = root_dir / "config" / "api_keys.yaml"
    
    if not api_keys_path.exists():
        print("❌ Файл config/api_keys.yaml не найден!")
        print(f"   Ожидается: {api_keys_path}")
        print()
        print("Создайте файл config/api_keys.yaml:")
        print("  openrouter_api_key: \"sk-or-v1-ваш-ключ-здесь\"")
        return False
    
    try:
        with open(api_keys_path, 'r', encoding='utf-8') as f:
            api_keys = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Ошибка чтения config/api_keys.yaml: {e}")
        return False
    
    # Получение API ключа (переменная окружения имеет приоритет)
    api_key = os.getenv('OPENROUTER_API_KEY') or api_keys.get('openrouter_api_key', '')
    base_url = 'https://openrouter.ai/api/v1'
    
    if not api_key:
        print("❌ API ключ не настроен в config/api_keys.yaml!")
        print("   Или установите переменную окружения OPENROUTER_API_KEY")
        return False
    
    if api_key == "your-openrouter-api-key-here":
        print("❌ API ключ не изменен (используется пример)!")
        print()
        print("Замените ключ в config/api_keys.yaml:")
        print('  openrouter_api_key: "sk-or-v1-ваш-ключ-здесь"')
        return False
    
    print(f"🔑 API ключ: {api_key[:20]}...{api_key[-10:]}")
    print(f"🌐 URL: {base_url}")
    print()
    
    # Проверка формата ключа
    if not api_key.startswith("sk-or-v1-"):
        print("⚠️  Предупреждение: ключ имеет неправильный формат!")
        print("   Ключи OpenRouter обычно начинаются с 'sk-or-v1-'")
        print()
    
    # Тестовый запрос к API
    print("📡 Отправка тестового запроса...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/stock-quotes-analyzer",
        "Content-Type": "application/json"
    }
    
    # Простой запрос для проверки аутентификации
    test_data = {
        "model": "openai/gpt-3.5-turbo",  # Дешевая модель для теста
        "messages": [
            {"role": "user", "content": "test"}
        ],
        "max_tokens": 5
    }
    
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=test_data,
            timeout=30
        )
        
        print(f"📊 Статус ответа: {response.status_code}")
        print()
        
        if response.status_code == 200:
            print("✅ API КЛЮЧ РАБОТАЕТ!")
            print()
            
            # Проверка баланса (если доступно)
            try:
                data = response.json()
                usage = data.get('usage', {})
                if usage:
                    print("📈 Использование:")
                    print(f"   - Промпт токенов: {usage.get('prompt_tokens', 0)}")
                    print(f"   - Всего токенов: {usage.get('total_tokens', 0)}")
            except:
                pass
            
            print()
            print("Можно запускать приложение:")
            print("  bin\\start_web.bat")
            
            return True
            
        elif response.status_code == 401:
            print("❌ API КЛЮЧ НЕДЕЙСТВИТЕЛЕН!")
            print()
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                print(f"Ошибка: {error_msg}")
            except:
                print(f"Ответ: {response.text}")
            
            print()
            print("ВОЗМОЖНЫЕ ПРИЧИНЫ:")
            print("1. Ключ просрочен или удален")
            print("2. Аккаунт не найден")
            print("3. Недостаточно средств на балансе")
            print()
            print("ЧТО ДЕЛАТЬ:")
            print("1. Перейдите на https://openrouter.ai/keys")
            print("2. Проверьте статус ключа")
            print("3. Создайте новый ключ если нужно")
            print("4. Проверьте баланс: https://openrouter.ai/credits")
            print("5. Обновите ключ в config/api_keys.yaml")
            
            return False
            
        elif response.status_code == 429:
            print("⚠️  ПРЕВЫШЕН ЛИМИТ ЗАПРОСОВ!")
            print()
            print("Слишком много запросов к API.")
            print("Подождите немного и попробуйте снова.")
            
            return False
            
        else:
            print(f"⚠️  НЕОЖИДАННЫЙ ОТВЕТ: {response.status_code}")
            print()
            print(f"Ответ: {response.text[:500]}")
            
            return False
            
    except requests.exceptions.Timeout:
        print("❌ ТАЙМАУТ!")
        print()
        print("Не удалось подключиться к API за 30 секунд.")
        print("Проверьте интернет-соединение.")
        
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ ОШИБКА ПОДКЛЮЧЕНИЯ!")
        print()
        print("Не удалось подключиться к OpenRouter API.")
        print("Проверьте:")
        print("1. Интернет-соединение")
        print("2. Настройки прокси/firewall")
        print("3. Доступность https://openrouter.ai")
        
        return False
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        
        return False


if __name__ == "__main__":
    success = test_api_key()
    print()
    print("="*70)
    sys.exit(0 if success else 1)
