"""
Проверка полноты документации v3.0
"""

import sys
from pathlib import Path

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

print("\n" + "="*70)
print("ПРОВЕРКА ДОКУМЕНТАЦИИ v3.0")
print("="*70 + "\n")

# Основные файлы документации
docs = {
    "README.md": "Основная документация проекта",
    "QUICK_START_V3.md": "Быстрый старт для v3.0",
    "WHATS_NEW_V3.md": "Что нового в v3.0",
    "CHANGELOG_CONFIG.md": "История изменений конфигурации",
    "CHANGELOG_PROMPTS.md": "История изменений промптов",
    "SUMMARY_CHANGES.md": "Полная сводка изменений",
    "docs/ru/МИГРАЦИЯ_V3.md": "Руководство по миграции (русский)",
    "docs/en/MIGRATION_V3.md": "Руководство по миграции (English)",
}

# Конфигурация
config_files = {
    "config/api_keys.example.yaml": "Пример API ключей",
    "config/llm_config.example.yaml": "Пример конфигурации LLM",
    "config/companies.example.json": "Пример списка компаний",
}

# Тесты
test_files = {
    "test_config_loading.py": "Тест загрузки конфигурации",
    "test_price_loading.py": "Тест получения котировок",
    "test_update_strategies.py": "Тест стратегий обновления",
    "check_current_db_data.py": "Проверка данных в БД",
}

print("[1] Основная документация:")
print("-"*70)
for file, desc in docs.items():
    path = Path(file)
    if path.exists():
        size = path.stat().st_size
        lines = len(path.read_text(encoding='utf-8').splitlines())
        print(f"   [OK] {file}")
        print(f"        {desc}")
        print(f"        Размер: {size:,} байт, строк: {lines}")
    else:
        print(f"   [!!] {file} - НЕ НАЙДЕН!")
    print()

print("\n[2] Файлы конфигурации:")
print("-"*70)
for file, desc in config_files.items():
    path = Path(file)
    if path.exists():
        size = path.stat().st_size
        print(f"   [OK] {file}")
        print(f"        {desc}")
        print(f"        Размер: {size:,} байт")
    else:
        print(f"   [!!] {file} - НЕ НАЙДЕН!")
    print()

print("\n[3] Тестовые скрипты:")
print("-"*70)
for file, desc in test_files.items():
    path = Path(file)
    if path.exists():
        size = path.stat().st_size
        print(f"   [OK] {file}")
        print(f"        {desc}")
        print(f"        Размер: {size:,} байт")
    else:
        print(f"   [!!] {file} - НЕ НАЙДЕН!")
    print()

print("\n[4] Проверка README.md:")
print("-"*70)
readme = Path("README.md").read_text(encoding='utf-8')

# Ключевые разделы, которые должны быть
required_sections = [
    "## ⚙️ Где находятся все настройки",
    "### 🔑 1. API ключи: `config/api_keys.yaml`",
    "### ⚙️ 2. Основные настройки: `config/llm_config.yaml`",
    "### 🏢 3. Список компаний: `config/companies.json`",
    "## 📖 Примеры использования",
    "## 🤝 Поддержка и Troubleshooting",
]

print("   Проверка ключевых разделов:")
for section in required_sections:
    if section in readme:
        print(f"   [OK] {section}")
    else:
        print(f"   [!!] ОТСУТСТВУЕТ: {section}")

print("\n" + "="*70)
print("[OK] ПРОВЕРКА ЗАВЕРШЕНА!")
print("="*70 + "\n")

print("Статистика:")
print(f"  - Файлов документации: {len([f for f in docs if Path(f).exists()])}/{len(docs)}")
print(f"  - Файлов конфигурации: {len([f for f in config_files if Path(f).exists()])}/{len(config_files)}")
print(f"  - Тестовых скриптов: {len([f for f in test_files if Path(f).exists()])}/{len(test_files)}")
print(f"  - README.md: {len(readme):,} символов, {len(readme.splitlines())} строк")
print()
