"""
Скрипт миграции проекта Stock Quotes на версию 3.0

Выполняет:
1. Экспорт списка компаний из БД в config/companies.json
2. Создание config/api_keys.yaml и config/llm_config.yaml из config.yaml
3. Опционально: очистка БД (удаление котировок, сохранение компаний)
4. Удаление старого файла data/samples/Stock quotes.xlsx
5. Проверка работоспособности новой конфигурации
"""

import sys
import os
import yaml
import json
import shutil
from pathlib import Path
from datetime import datetime

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Добавление корневой директории в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database


def print_header():
    """Вывод заголовка"""
    print("\n" + "="*60)
    print("  Миграция Stock Quotes на версию 3.0")
    print("="*60 + "\n")


def check_old_config() -> dict:
    """
    Проверка наличия старого config.yaml
    
    Returns:
        Словарь конфигурации или None
    """
    config_path = Path("config.yaml")
    
    if not config_path.exists():
        print("[X] Файл config.yaml не найден!")
        print("    Миграция возможна только при наличии config.yaml")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("[OK] Найден config.yaml")
        return config
    
    except Exception as e:
        print(f"[X] Ошибка чтения config.yaml: {e}")
        return None


def export_companies_from_db(db_path: str) -> list:
    """
    Экспорт компаний из БД
    
    Args:
        db_path: Путь к БД
        
    Returns:
        Список компаний
    """
    print("\n1. Экспорт компаний из БД...")
    
    try:
        db = Database(db_path)
        
        db.cursor.execute("SELECT ticker, name, sector, industry FROM companies ORDER BY ticker")
        companies = []
        
        for row in db.cursor.fetchall():
            companies.append({
                'ticker': row['ticker'],
                'name': row['name'] or '',
                'sector': row['sector'] or '',
                'industry': row['industry'] or ''
            })
        
        db.close()
        
        print(f"   [+] Найдено компаний: {len(companies)}")
        
        if companies:
            print(f"   Примеры: {', '.join([c['ticker'] for c in companies[:5]])}")
        
        return companies
    
    except Exception as e:
        print(f"   [X] Ошибка экспорта: {e}")
        return []


def create_config_files(config: dict, companies: list) -> bool:
    """
    Создание новых файлов конфигурации
    
    Args:
        config: Старая конфигурация
        companies: Список компаний
        
    Returns:
        True если успешно
    """
    print("\n2. Создание новых файлов конфигурации...")
    
    try:
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        # api_keys.yaml
        api_keys = {
            'openrouter_api_key': config.get('openrouter', {}).get('api_key', ''),
            'alphavantage_api_key': config.get('company_info', {}).get('alphavantage_api_key', '')
        }
        
        api_keys_path = config_dir / "api_keys.yaml"
        with open(api_keys_path, 'w', encoding='utf-8') as f:
            yaml.dump(api_keys, f, allow_unicode=True, default_flow_style=False)
        
        print(f"   [+] {api_keys_path}")
        
        # llm_config.yaml
        llm_config = {
            'openrouter': {
                'base_url': config.get('openrouter', {}).get('base_url', 'https://openrouter.ai/api/v1')
            },
            'models': config.get('models', []),
            'system_prompt': config.get('system_prompt', ''),
            'prompt_template': config.get('prompt_template', ''),
            'database': config.get('database', {}),
            'export': config.get('export', {}),
            'company_info': {
                'fallback_to_llm': config.get('company_info', {}).get('fallback_to_llm', True),
                'cache_duration_days': config.get('company_info', {}).get('cache_duration_days', 30),
                'llm_model': config.get('company_info', {}).get('llm_model', 'openai/gpt-3.5-turbo')
            },
            'scheduler': config.get('scheduler', {}),
            'web_app': config.get('web_app', {}),
            'logging': config.get('logging', {})
        }
        
        llm_config_path = config_dir / "llm_config.yaml"
        with open(llm_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(llm_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        print(f"   [+] {llm_config_path}")
        
        # companies.json
        companies_data = {
            'companies': companies,
            'last_updated': datetime.now().isoformat()
        }
        
        companies_path = config_dir / "companies.json"
        with open(companies_path, 'w', encoding='utf-8') as f:
            json.dump(companies_data, f, ensure_ascii=False, indent=2)
        
        print(f"   [+] {companies_path}")
        
        return True
    
    except Exception as e:
        print(f"   [X] Ошибка создания файлов: {e}")
        return False


def clear_database(db_path: str) -> bool:
    """
    Очистка БД (опционально)
    
    Args:
        db_path: Путь к БД
        
    Returns:
        True если успешно
    """
    print("\n3. Очистка базы данных...")
    
    response = input("   Очистить БД (удалить котировки и анализы, сохранить компании)? [y/N]: ").strip().lower()
    
    if response != 'y':
        print("   [-] Пропущено")
        return True
    
    try:
        db = Database(db_path)
        
        # Подсчет записей
        db.cursor.execute("SELECT COUNT(*) FROM stocks")
        stocks_count = db.cursor.fetchone()[0]
        
        db.cursor.execute("SELECT COUNT(*) FROM analysis_results")
        analyses_count = db.cursor.fetchone()[0]
        
        # Удаление данных
        db.cursor.execute("DELETE FROM accuracy_history")
        db.cursor.execute("DELETE FROM consensus")
        db.cursor.execute("DELETE FROM analysis_results")
        db.cursor.execute("DELETE FROM price_sources")
        db.cursor.execute("DELETE FROM stocks")
        
        db.conn.commit()
        db.close()
        
        print(f"   [+] Удалено котировок: {stocks_count}")
        print(f"   [+] Удалено анализов: {analyses_count}")
        print("   [+] Компании сохранены")
        
        return True
    
    except Exception as e:
        print(f"   [X] Ошибка очистки БД: {e}")
        return False


def remove_old_excel() -> bool:
    """
    Удаление старого Excel файла
    
    Returns:
        True если успешно
    """
    print("\n4. Удаление старого Excel файла...")
    
    excel_path = Path("data/samples/Stock quotes.xlsx")
    
    if not excel_path.exists():
        print("   [-] Файл не найден, пропущено")
        return True
    
    response = input(f"   Удалить {excel_path}? [y/N]: ").strip().lower()
    
    if response != 'y':
        print("   [-] Пропущено")
        return True
    
    try:
        # Создание резервной копии
        backup_path = excel_path.parent / f"Stock quotes_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        shutil.copy2(excel_path, backup_path)
        print(f"   [+] Создана резервная копия: {backup_path}")
        
        # Удаление оригинала
        excel_path.unlink()
        print(f"   [+] Файл удален")
        
        return True
    
    except Exception as e:
        print(f"   [X] Ошибка удаления: {e}")
        return False


def backup_old_config() -> bool:
    """
    Создание резервной копии config.yaml
    
    Returns:
        True если успешно
    """
    print("\n5. Резервное копирование config.yaml...")
    
    config_path = Path("config.yaml")
    
    if not config_path.exists():
        return True
    
    try:
        backup_path = Path(f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
        shutil.copy2(config_path, backup_path)
        print(f"   [+] Создана резервная копия: {backup_path}")
        
        response = input("   Удалить оригинальный config.yaml? [y/N]: ").strip().lower()
        
        if response == 'y':
            config_path.unlink()
            print("   [+] config.yaml удален")
        else:
            print("   [-] config.yaml сохранен (можно удалить вручную)")
        
        return True
    
    except Exception as e:
        print(f"   [X] Ошибка резервного копирования: {e}")
        return False


def verify_migration() -> bool:
    """
    Проверка успешности миграции
    
    Returns:
        True если все ОК
    """
    print("\n6. Проверка миграции...")
    
    config_dir = Path("config")
    required_files = [
        config_dir / "api_keys.yaml",
        config_dir / "llm_config.yaml",
        config_dir / "companies.json"
    ]
    
    all_ok = True
    
    for file_path in required_files:
        if file_path.exists():
            print(f"   [+] {file_path}")
        else:
            print(f"   [X] {file_path} не найден!")
            all_ok = False
    
    return all_ok


def main():
    """Главная функция"""
    print_header()
    
    # Проверка старой конфигурации
    config = check_old_config()
    if not config:
        print("\n[X] Миграция прервана")
        return 1
    
    # Экспорт компаний
    db_path = config.get('database', {}).get('path', 'data/stock_analysis.db')
    companies = export_companies_from_db(db_path)
    
    if not companies:
        print("\n[!] В БД нет компаний. Будет создан пустой companies.json")
        companies = []
    
    # Создание новых файлов
    if not create_config_files(config, companies):
        print("\n[X] Миграция прервана")
        return 1
    
    # Очистка БД
    if not clear_database(db_path):
        print("\n[!] Ошибка очистки БД, но миграция продолжается")
    
    # Удаление Excel
    if not remove_old_excel():
        print("\n[!] Ошибка удаления Excel, но миграция продолжается")
    
    # Резервное копирование config.yaml
    if not backup_old_config():
        print("\n[!] Ошибка резервного копирования, но миграция продолжается")
    
    # Проверка
    if verify_migration():
        print("\n" + "="*60)
        print("[OK] Миграция завершена успешно!")
        print("="*60)
        print("\nСледующие шаги:")
        print("1. Проверьте файлы в папке config/")
        print("2. Убедитесь, что API ключи корректны")
        print("3. Запустите приложение: python main.py или streamlit run app.py")
        print("4. При успешной работе удалите резервные копии")
        print("\n")
        return 0
    else:
        print("\n[X] Миграция завершена с ошибками")
        print("    Проверьте файлы конфигурации вручную")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[!] Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
