"""
Скрипт для проверки всех путей и конфигурации проекта
"""

import os
import sys
from pathlib import Path
import yaml

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def check_paths():
    """Проверка всех критичных путей в проекте"""
    print("="*70)
    print("ПРОВЕРКА ПУТЕЙ И КОНФИГУРАЦИИ ПРОЕКТА")
    print("="*70)
    print()
    
    errors = []
    warnings = []
    
    # Корень проекта
    root = Path(__file__).parent.parent
    os.chdir(root)
    
    print(f"📂 Корень проекта: {root}")
    print()
    
    # Проверка структуры папок
    print("1. СТРУКТУРА ПАПОК")
    print("-" * 70)
    required_dirs = [
        "bin",
        "docs/en",
        "docs/ru",
        "scripts",
        "src",
        "src/dashboards",
        "data/samples",
        "data/cache",
        "output/exports",
        "logs",
        "deploy"
    ]
    
    for dir_path in required_dirs:
        full_path = root / dir_path
        if full_path.exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path} - НЕ НАЙДЕНА!")
            errors.append(f"Отсутствует папка: {dir_path}")
    
    print()
    
    # Проверка файлов
    print("2. КРИТИЧНЫЕ ФАЙЛЫ")
    print("-" * 70)
    required_files = [
        "config/api_keys.yaml",
        "config/llm_config.yaml",
        "main.py",
        "app.py",
        "scheduler.py",
        "requirements.txt",
        "README.md",
        ".gitignore",
        "src/__init__.py",
        "src/data_loader.py",
        "src/database.py",
        "src/analyzer.py",
        "src/llm_manager.py",
        "src/excel_exporter.py",
        "src/company_info.py",
        "src/dashboards/__init__.py",
        "src/dashboards/overview.py",
        "src/dashboards/analysis.py",
        "src/dashboards/history.py",
        "src/dashboards/accuracy.py",
        "src/dashboards/settings.py",
        "data/samples/Stock quotes.xlsx"
    ]
    
    for file_path in required_files:
        full_path = root / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"✅ {file_path} ({size} bytes)")
        else:
            print(f"❌ {file_path} - НЕ НАЙДЕН!")
            errors.append(f"Отсутствует файл: {file_path}")
    
    print()
    
    # Проверка конфигурации
    print("3. КОНФИГУРАЦИЯ")
    print("-" * 70)
    
    api_keys_path = root / "config" / "api_keys.yaml"
    llm_config_path = root / "config" / "llm_config.yaml"
    
    if api_keys_path.exists() and llm_config_path.exists():
        try:
            # Загрузка API ключей
            with open(api_keys_path, 'r', encoding='utf-8') as f:
                api_keys = yaml.safe_load(f)
            
            # Загрузка LLM конфигурации
            with open(llm_config_path, 'r', encoding='utf-8') as f:
                llm_config = yaml.safe_load(f)
            
            # Проверка API ключа
            api_key = api_keys.get('openrouter_api_key', '')
            if not api_key:
                print("❌ API ключ не настроен!")
                errors.append("API ключ отсутствует в config/api_keys.yaml")
            elif api_key == "your-openrouter-api-key-here":
                print("❌ API ключ не изменен (используется пример)!")
                errors.append("API ключ не изменен с примера")
            elif not api_key.startswith("sk-or-v1-"):
                print("⚠️  API ключ имеет неправильный формат!")
                warnings.append("API ключ должен начинаться с 'sk-or-v1-'")
            else:
                print(f"✅ API ключ настроен: {api_key[:20]}...")
                print("⚠️  ВНИМАНИЕ: Ошибка 401 означает, что ключ недействителен!")
                print("   Проверьте:")
                print("   1. Ключ актуален на https://openrouter.ai/keys")
                print("   2. На балансе есть средства")
                print("   3. Ключ не удален и не просрочен")
            
            # Проверка моделей
            models = llm_config.get('models', [])
            print(f"\n✅ Настроено моделей: {len(models)}")
            for model in models:
                print(f"   - {model.get('name')}: {model.get('id')}")
            
            # Проверка пути к файлу данных
            companies_path = root / "config" / "companies.json"
            if companies_path.exists():
                size = companies_path.stat().st_size / 1024  # KB
                print(f"\n✅ Список компаний: config/companies.json ({size:.1f} KB)")
            else:
                excel_file = llm_config.get('input', {}).get('excel_file', '')
                if excel_file:
                    excel_path = root / excel_file
                    if excel_path.exists():
                        size = excel_path.stat().st_size / 1024  # KB
                        print(f"\n✅ Путь к данным: {excel_file} ({size:.1f} KB)")
                    else:
                        print(f"\n❌ Путь к данным: {excel_file} - ФАЙЛ НЕ НАЙДЕН!")
                        errors.append(f"Файл данных не найден: {excel_file}")
                else:
                    print(f"\n⚠️  Файл компаний не указан")
            
            # Проверка БД
            db_path = root / llm_config.get('database', {}).get('path', 'data/stock_analysis.db')
            if db_path.exists():
                size = db_path.stat().st_size / 1024  # KB
                print(f"✅ База данных: {db_path.name} ({size:.1f} KB)")
            else:
                print(f"⚠️  База данных не найдена (будет создана при первом запуске)")
            
        except Exception as e:
            print(f"❌ Ошибка чтения конфигурации: {e}")
            errors.append(f"Ошибка чтения конфигурации: {e}")
    else:
        print("❌ Файлы конфигурации не найдены!")
        if not api_keys_path.exists():
            print(f"   ❌ Отсутствует: config/api_keys.yaml")
            errors.append("Файл config/api_keys.yaml не найден")
        if not llm_config_path.exists():
            print(f"   ❌ Отсутствует: config/llm_config.yaml")
            errors.append("Файл config/llm_config.yaml не найден")
    
    print()
    
    # Проверка bat файлов
    print("4. СКРИПТЫ ЗАПУСКА")
    print("-" * 70)
    bat_files = [
        "bin/setup.bat",
        "bin/start.bat",
        "bin/start_web.bat",
        "bin/start_scheduler.bat",
        "bin/quick_start.bat",
        "bin/check_dependencies.bat",
        "bin/clear_database.bat"
    ]
    
    for bat_file in bat_files:
        full_path = root / bat_file
        if full_path.exists():
            print(f"✅ {bat_file}")
        else:
            print(f"❌ {bat_file} - НЕ НАЙДЕН!")
            errors.append(f"Отсутствует скрипт: {bat_file}")
    
    print()
    
    # Итоги
    print("="*70)
    print("ИТОГИ ПРОВЕРКИ")
    print("="*70)
    
    if not errors and not warnings:
        print("✅ Проект полностью настроен и готов к работе!")
    else:
        if errors:
            print(f"\n❌ Найдено ошибок: {len(errors)}")
            for i, error in enumerate(errors, 1):
                print(f"   {i}. {error}")
        
        if warnings:
            print(f"\n⚠️  Найдено предупреждений: {len(warnings)}")
            for i, warning in enumerate(warnings, 1):
                print(f"   {i}. {warning}")
    
    print()
    print("="*70)
    print("РЕШЕНИЕ ПРОБЛЕМЫ С API")
    print("="*70)
    print("""
⚠️  ОШИБКА 401 "User not found" означает:

1. API ключ недействителен или просрочен
2. Аккаунт не найден или заблокирован
3. Баланс исчерпан

ЧТО ДЕЛАТЬ:

1. Перейдите на https://openrouter.ai/keys
2. Проверьте статус ключа
3. Если ключ удален - создайте новый
4. Проверьте баланс на https://openrouter.ai/credits
5. Пополните баланс если нужно ($5-10 для начала)
6. Обновите ключ в config/api_keys.yaml:
   
   openrouter_api_key: "sk-or-v1-ваш-новый-ключ"

7. Перезапустите приложение

ПРОВЕРКА КЛЮЧА:
Используйте скрипт для проверки ключа перед запуском:
    python scripts/test_api_key.py
    """)
    
    return len(errors) == 0


if __name__ == "__main__":
    success = check_paths()
    sys.exit(0 if success else 1)
