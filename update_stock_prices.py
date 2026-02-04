"""
Скрипт для обновления котировок акций в базе данных
Используйте этот скрипт чтобы внести реальные цены вручную
"""

import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.database import Database
from datetime import date

# Примерные текущие цены полупроводниковых компаний (ПРИМЕР - замените на реальные!)
# Источник: можно взять с finance.yahoo.com, investing.com и т.д.
STOCK_PRICES = {
    'NVDA': {'price': 875.28, 'change': -2.8, 'volume': 42000000},
    'AVGO': {'price': 1450.50, 'change': 1.2, 'volume': 2800000},
    'TSM': {'price': 145.60, 'change': -0.5, 'volume': 12000000},
    'ASMLF': {'price': 1025.30, 'change': 0.8, 'volume': 450000},
    'ASML': {'price': 1025.30, 'change': 0.8, 'volume': 450000},  # Те же данные
    'MU': {'price': 88.45, 'change': -1.2, 'volume': 18000000},
    'AMD': {'price': 178.90, 'change': 2.5, 'volume': 45000000},
    'LRCX': {'price': 825.60, 'change': -0.3, 'volume': 1200000},
    'AMAT': {'price': 195.75, 'change': 1.8, 'volume': 6500000},
    'INTC': {'price': 42.30, 'change': -3.5, 'volume': 52000000},
}

def update_prices(dry_run=False):
    """
    Обновление цен в базе данных
    
    Args:
        dry_run: Если True, только показать что будет сделано, не сохранять
    """
    db = Database('data/stock_analysis.db')
    today = date.today()
    
    print("=" * 80)
    print("🔄 ОБНОВЛЕНИЕ КОТИРОВОК В БАЗЕ ДАННЫХ")
    print("=" * 80)
    print()
    
    if dry_run:
        print("⚠️  РЕЖИМ ПРЕДПРОСМОТРА (изменения не сохраняются)")
        print()
    
    updated_count = 0
    
    for ticker, data in STOCK_PRICES.items():
        # Проверяем существование компании
        db.cursor.execute("SELECT id FROM companies WHERE ticker = ?", (ticker,))
        company = db.cursor.fetchone()
        
        if not company:
            print(f"⚠️  {ticker:8s} - компания не найдена в БД, пропускаем")
            continue
        
        company_id = company[0]
        
        if not dry_run:
            # Обновляем или создаем котировку
            db.cursor.execute("""
                SELECT id FROM stocks 
                WHERE company_id = ? AND analysis_date = ?
            """, (company_id, today))
            
            existing = db.cursor.fetchone()
            
            if existing:
                # Обновляем существующую
                db.cursor.execute("""
                    UPDATE stocks 
                    SET price = ?, change_percent = ?, volume = ?
                    WHERE id = ?
                """, (data['price'], data['change'], data['volume'], existing[0]))
            else:
                # Создаем новую
                db.cursor.execute("""
                    INSERT INTO stocks 
                    (company_id, price, change_percent, volume, analysis_date)
                    VALUES (?, ?, ?, ?, ?)
                """, (company_id, data['price'], data['change'], data['volume'], today))
        
        change_sign = "+" if data['change'] > 0 else ""
        print(f"✅ {ticker:8s} - ${data['price']:8.2f} | {change_sign}{data['change']:6.2f}% | {data['volume']:12,d}")
        updated_count += 1
    
    if not dry_run:
        db.conn.commit()
        print()
        print(f"✅ Обновлено {updated_count} котировок в базе данных")
    else:
        print()
        print(f"📊 Будет обновлено {updated_count} котировок")
        print()
        print("Для применения изменений запустите:")
        print("  python update_stock_prices.py --apply")
    
    db.close()
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Обновление котировок в БД')
    parser.add_argument('--apply', action='store_true', 
                       help='Применить изменения (иначе только предпросмотр)')
    
    args = parser.parse_args()
    
    if args.apply:
        print()
        print("⚠️  ВНИМАНИЕ: Цены в скрипте являются ПРИМЕРОМ!")
        print("    Обновите словарь STOCK_PRICES реальными данными перед применением")
        print()
        response = input("Продолжить? (yes/no): ")
        if response.lower() != 'yes':
            print("Отменено")
            sys.exit(0)
        update_prices(dry_run=False)
    else:
        update_prices(dry_run=True)
