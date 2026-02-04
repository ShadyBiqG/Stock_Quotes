"""
Скрипт для проверки состояния базы данных
"""

import sys
import codecs

# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.database import Database
from pathlib import Path


def check_database(db_path: str = "data/stock_analysis.db"):
    """
    Проверка состояния базы данных
    
    Args:
        db_path: Путь к БД
    """
    db_path = Path(db_path)
    
    if not db_path.exists():
        print(f"❌ База данных не найдена: {db_path}")
        return
    
    print(f"📊 Проверка базы данных: {db_path}")
    print(f"   Размер: {db_path.stat().st_size / 1024:.2f} KB")
    print()
    
    try:
        db = Database(str(db_path))
        
        # Подсчет записей
        db.cursor.execute("SELECT COUNT(*) FROM companies")
        companies_count = db.cursor.fetchone()[0]
        
        db.cursor.execute("SELECT COUNT(*) FROM stocks")
        stocks_count = db.cursor.fetchone()[0]
        
        db.cursor.execute("SELECT COUNT(*) FROM analysis_results")
        analyses_count = db.cursor.fetchone()[0]
        
        db.cursor.execute("SELECT COUNT(*) FROM consensus")
        consensus_count = db.cursor.fetchone()[0]
        
        db.cursor.execute("SELECT COUNT(*) FROM accuracy_history")
        accuracy_count = db.cursor.fetchone()[0]
        
        print("📋 Статистика таблиц:")
        print(f"   Компаний:         {companies_count}")
        print(f"   Котировок:        {stocks_count}")
        print(f"   Анализов:         {analyses_count}")
        print(f"   Консенсусов:      {consensus_count}")
        print(f"   История точности: {accuracy_count}")
        print()
        
        if companies_count > 0:
            print("🏢 Компании в базе:")
            db.cursor.execute("""
                SELECT ticker, name, sector, 
                       (SELECT COUNT(*) FROM stocks WHERE company_id = companies.id) as stock_count
                FROM companies 
                ORDER BY ticker
            """)
            
            for row in db.cursor.fetchall():
                ticker = row[0]
                name = row[1] or "Без названия"
                sector = row[2] or "Неизвестно"
                stock_count = row[3]
                
                print(f"   • {ticker:8s} - {name[:30]:30s} | Сектор: {sector[:20]:20s} | Котировок: {stock_count}")
        else:
            print("⚠️  В базе данных нет компаний")
        
        print()
        
        if stocks_count > 0:
            print("📈 Последние котировки:")
            db.cursor.execute("""
                SELECT c.ticker, s.price, s.change_percent, s.volume, s.analysis_date
                FROM stocks s
                JOIN companies c ON s.company_id = c.id
                ORDER BY s.analysis_date DESC, s.created_at DESC
                LIMIT 10
            """)
            
            for row in db.cursor.fetchall():
                ticker = row[0]
                price = row[1]
                change = row[2]
                volume = row[3]
                date = row[4]
                
                change_sign = "+" if change > 0 else ""
                print(f"   • {ticker:8s} | ${price:8.2f} | {change_sign}{change:6.2f}% | {volume:12,d} | {date}")
        
        db.close()
        
        print()
        print("✅ Проверка завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка проверки БД: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_database("data/stock_analysis.db")
