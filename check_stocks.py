"""
Проверка котировок для тикеров
"""

import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.database import Database

db = Database('data/stock_analysis.db')

# Список тикеров из Excel
tickers = ['NVDA', 'AVGO', 'TSM', 'ASMLF', 'ASML', 'MU', 'AMD', 'LRCX', 'AMAT', 'INTC']

print("📊 ПРОВЕРКА КОТИРОВОК")
print("=" * 80)
print()

for ticker in tickers:
    # Проверяем есть ли компания
    db.cursor.execute("SELECT id, name FROM companies WHERE ticker = ?", (ticker,))
    company = db.cursor.fetchone()
    
    if not company:
        print(f"❌ {ticker:8s} - компания НЕ НАЙДЕНА в БД")
        continue
    
    company_id = company[0]
    company_name = company[1] or "Без названия"
    
    # Проверяем котировки
    db.cursor.execute("""
        SELECT price, change_percent, volume, analysis_date 
        FROM stocks 
        WHERE company_id = ? 
        ORDER BY analysis_date DESC, created_at DESC 
        LIMIT 1
    """, (company_id,))
    
    stock = db.cursor.fetchone()
    
    if stock:
        price = stock[0]
        change = stock[1]
        volume = stock[2]
        date = stock[3]
        print(f"✅ {ticker:8s} - ${price:8.2f} | {change:+6.2f}% | {date} | {company_name[:40]}")
    else:
        print(f"⚠️  {ticker:8s} - НЕТ КОТИРОВОК | {company_name[:40]}")

db.close()

print()
print("=" * 80)
