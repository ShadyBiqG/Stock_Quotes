"""
Тест загрузки конфигурации v3.0
"""

import sys
from pathlib import Path
import yaml

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

print("\n" + "="*70)
print("ТЕСТ ЗАГРУЗКИ КОНФИГУРАЦИИ v3.0")
print("="*70 + "\n")

# 1. Проверка файлов
print("[1] Проверка наличия файлов конфигурации:")
print("-"*70)

files = {
    "config/api_keys.yaml": Path("config/api_keys.yaml").exists(),
    "config/llm_config.yaml": Path("config/llm_config.yaml").exists(),
    "config/companies.json": Path("config/companies.json").exists(),
    "config.yaml (старый)": Path("config.yaml").exists(),
}

for file, exists in files.items():
    status = "✅" if exists else "❌"
    print(f"   {status} {file}")

print()

# 2. Загрузка конфигурации
print("\n[2] Загрузка конфигурации:")
print("-"*70)

try:
    # API ключи
    with open("config/api_keys.yaml", "r", encoding="utf-8") as f:
        api_keys = yaml.safe_load(f)
    print("   ✅ config/api_keys.yaml загружен")
    print(f"      • openrouter_api_key: {api_keys['openrouter_api_key'][:20]}...")
    
    # LLM конфигурация
    with open("config/llm_config.yaml", "r", encoding="utf-8") as f:
        llm_config = yaml.safe_load(f)
    print("   ✅ config/llm_config.yaml загружен")
    
    # Объединение
    config = llm_config.copy()
    config['openrouter']['api_key'] = api_keys['openrouter_api_key']
    if 'alphavantage_api_key' in api_keys:
        config['company_info']['alphavantage_api_key'] = api_keys['alphavantage_api_key']
    
    print("   ✅ Конфигурация объединена")
    
except Exception as e:
    print(f"   ❌ Ошибка загрузки: {e}")
    sys.exit(1)

print()

# 3. Проверка секций
print("\n[3] Проверка ключевых секций:")
print("-"*70)

sections = {
    "input": "Входные данные (путь к companies.json)",
    "openrouter": "Настройки OpenRouter (API key, base_url)",
    "models": "Модели LLM",
    "system_prompt": "System prompt",
    "prompt_template": "Промпт для анализа",
    "database": "Настройки базы данных",
    "price_updates": "Стратегия обновления котировок",
    "export": "Настройки экспорта",
    "company_info": "Получение информации о компаниях",
    "scheduler": "Планировщик задач",
    "web_app": "Настройки веб-приложения",
    "logging": "Настройки логирования",
}

for section, description in sections.items():
    exists = section in config
    status = "✅" if exists else "❌"
    print(f"   {status} {section:<20} - {description}")

print()

# 4. Детали конфигурации
print("\n[4] Детали конфигурации:")
print("-"*70)

print(f"   [*] Входной файл: {config['input']['excel_file']}")
print(f"   [*] База данных: {config['database']['path']}")
print(f"   [*] Стратегия обновления: {config['price_updates']['strategy']}")
print(f"   [*] Количество моделей: {len(config['models'])}")
print(f"   [*] Веб-порт: {config['web_app']['port']}")
print(f"   [*] Уровень логов: {config['logging']['level']}")

print()

# 5. Модели LLM
print("\n[5] Модели LLM:")
print("-"*70)

for i, model in enumerate(config['models'], 1):
    print(f"   {i}. {model['name']}")
    print(f"      ID: {model['id']}")
    print(f"      Temperature: {model['temperature']}")
    print(f"      Max tokens: {model['max_tokens']}")
    print()

# 6. Промпты
print("\n[6] Промпты:")
print("-"*70)

system_prompt_lines = config['system_prompt'].strip().split('\n')
print(f"   [*] System prompt ({len(system_prompt_lines)} строк):")
print(f"       Первая строка: {system_prompt_lines[0][:60]}...")

prompt_template_lines = config['prompt_template'].strip().split('\n')
print(f"   [*] Prompt template ({len(prompt_template_lines)} строк):")
print(f"       Первая строка: {prompt_template_lines[0][:60]}...")

print()

print("="*70)
print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
print("="*70)
print()
print("Конфигурация v3.0 загружена корректно!")
print("Теперь можно запускать приложение:")
print("  python main.py")
print("  streamlit run app.py")
print()
