"""
Тест загрузки данных через систему
"""

import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data_loader import load_stock_data
from src.database import Database

print("=" * 80)
print("🧪 ТЕСТ ЗАГРУЗКИ ДАННЫХ")
print("=" * 80)
print()

# Загрузка с использованием БД
db = Database('data/stock_analysis.db')
stocks = load_stock_data('Stock quotes.xlsx', database=db)
db.close()

print(f"✅ Загружено {len(stocks)} акций из Excel + БД")
print()
print("Данные:")
print("-" * 80)

for stock in stocks:
    ticker = stock['ticker']
    price = stock['price']
    change = stock['change']
    volume = stock['volume']
    
    change_sign = "+" if change > 0 else ""
    print(f"{ticker:8s} | ${price:10.2f} | {change_sign}{change:6.2f}% | {volume:15,d}")

print("-" * 80)
print()
print("=" * 80)
