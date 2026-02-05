"""
Скрипт для полной очистки базы данных
Удаляет все записи из всех таблиц для развертывания с чистого листа
"""

import sqlite3
import logging
from pathlib import Path
import sys

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clear_database(db_path: str = "data/stocks.db", delete_file: bool = False) -> None:
    """
    Очистка базы данных
    
    Args:
        db_path: Путь к файлу базы данных
        delete_file: Если True - удалить файл БД, если False - очистить таблицы
    """
    db_file = Path(db_path)
    
    if not db_file.exists():
        logger.warning(f"База данных не найдена: {db_path}")
        print(f"\n⚠️  База данных не существует: {db_path}")
        print("   Ничего не нужно очищать!")
        return
    
    if delete_file:
        # Вариант 1: Удаление файла БД
        logger.info(f"Удаление файла базы данных: {db_path}")
        print(f"\n🗑️  Удаление файла базы данных...")
        
        try:
            db_file.unlink()
            logger.info("Файл базы данных успешно удален")
            print(f"✅ База данных удалена: {db_path}")
            print("   При следующем запуске будет создана новая чистая БД")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла БД: {e}")
            print(f"❌ Ошибка при удалении: {e}")
            raise
    else:
        # Вариант 2: Очистка всех таблиц
        logger.info(f"Очистка всех таблиц в БД: {db_path}")
        print(f"\n🧹 Очистка всех таблиц в базе данных...")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Список всех таблиц для очистки (порядок важен из-за foreign keys)
            tables = [
                'accuracy_history',    # Сначала удаляем зависимые таблицы
                'consensus',
                'analysis_results',
                'price_sources',       # v3.0: таблица источников цен
                'stocks',
                'companies'            # В последнюю очередь главные таблицы
            ]
            
            # Подсчет записей перед очисткой
            total_records = 0
            existing_tables = []
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    total_records += count
                    existing_tables.append(table)
                    if count > 0:
                        print(f"   📊 {table}: {count} записей")
                except sqlite3.OperationalError:
                    # Таблица не существует - пропускаем
                    pass
            
            print(f"\n   Всего записей: {total_records}")
            
            if total_records == 0:
                print("\n✅ База данных уже пуста!")
                conn.close()
                return
            
            # Очистка таблиц
            for table in existing_tables:
                cursor.execute(f"DELETE FROM {table}")
                logger.info(f"Очищена таблица: {table}")
            
            # Сброс счетчиков автоинкремента
            for table in existing_tables:
                try:
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                except sqlite3.OperationalError:
                    pass
            
            conn.commit()
            conn.close()
            
            logger.info("База данных успешно очищена")
            print(f"\n✅ Все таблицы очищены!")
            print(f"   Удалено записей: {total_records}")
            print("   Структура БД сохранена")
            
        except Exception as e:
            logger.error(f"Ошибка при очистке таблиц: {e}")
            print(f"❌ Ошибка при очистке: {e}")
            if conn:
                conn.rollback()
                conn.close()
            raise


def show_database_info(db_path: str = "data/stocks.db") -> None:
    """
    Показать информацию о содержимом БД
    
    Args:
        db_path: Путь к файлу базы данных
    """
    db_file = Path(db_path)
    
    if not db_file.exists():
        print(f"\n⚠️  База данных не существует: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print("📊 ИНФОРМАЦИЯ О БАЗЕ ДАННЫХ")
        print("="*60)
        print(f"Файл: {db_path}")
        print(f"Размер: {db_file.stat().st_size / 1024:.2f} KB")
        print()
        
        tables = [
            ('companies', 'Компании'),
            ('stocks', 'Котировки'),
            ('analysis_results', 'Результаты анализа'),
            ('consensus', 'Консенсус'),
            ('accuracy_history', 'История точности'),
            ('price_sources', 'Источники цен')
        ]
        
        total_records = 0
        for table, description in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                total_records += count
                print(f"  {description:25s}: {count:6d} записей")
            except sqlite3.OperationalError:
                # Таблица не существует
                print(f"  {description:25s}: (таблица отсутствует)")
        
        print(f"\n  {'ИТОГО':25s}: {total_records:6d} записей")
        print("="*60)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при чтении БД: {e}")


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Очистка базы данных Stock Quotes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  1. Показать информацию о БД:
     python clear_database.py --info

  2. Очистить все таблицы (рекомендуется):
     python clear_database.py --clear

  3. Удалить файл БД полностью:
     python clear_database.py --delete

  4. Без подтверждения (для автоматизации):
     python clear_database.py --clear --force
        """
    )
    
    parser.add_argument(
        '--info',
        action='store_true',
        help='Показать информацию о содержимом БД'
    )
    
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Очистить все таблицы (структура БД сохраняется)'
    )
    
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Удалить файл БД полностью'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Не запрашивать подтверждение'
    )
    
    parser.add_argument(
        '--db-path',
        default='data/stocks.db',
        help='Путь к файлу БД (по умолчанию: data/stocks.db)'
    )
    
    args = parser.parse_args()
    
    # Баннер
    print("\n" + "="*60)
    print("  🗑️  ОЧИСТКА БАЗЫ ДАННЫХ STOCK QUOTES")
    print("="*60)
    
    # Показать информацию
    if args.info or (not args.clear and not args.delete):
        show_database_info(args.db_path)
        
        if not args.clear and not args.delete:
            print("\n💡 Используйте --clear или --delete для очистки БД")
            print("   Справка: python clear_database.py --help")
        return
    
    # Очистка или удаление
    db_file = Path(args.db_path)
    if not db_file.exists():
        print(f"\n⚠️  База данных не существует: {args.db_path}")
        print("   Ничего не нужно очищать!")
        return
    
    # Показать текущее состояние
    show_database_info(args.db_path)
    
    # Подтверждение
    if not args.force:
        print("\n⚠️  ВНИМАНИЕ!")
        if args.delete:
            print("   Будет УДАЛЕН файл базы данных!")
        else:
            print("   Будут УДАЛЕНЫ все записи из всех таблиц!")
        
        print("   Это действие НЕОБРАТИМО!")
        print()
        
        response = input("   Продолжить? (yes/NO): ").strip().lower()
        if response not in ['yes', 'y', 'да']:
            print("\n❌ Операция отменена")
            return
    
    # Выполнение очистки
    try:
        clear_database(args.db_path, delete_file=args.delete)
        
        print("\n✨ Готово!")
        print("   База данных очищена и готова к развертыванию с чистого листа")
        
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")
        logger.exception("Ошибка при очистке БД")
        sys.exit(1)


if __name__ == "__main__":
    main()
