"""
Сравнение тикеров в Excel и БД
"""

import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import pandas as pd
from src.database import Database

# Читаем тикеры из Excel
df = pd.read_excel('Stock quotes.xlsx')
excel_tickers = set(df['Ticker'].tolist())

# Читаем тикеры из БД
db = Database('data/stock_analysis.db')
db.cursor.execute('SELECT ticker FROM companies ORDER BY ticker')
db_tickers = set([row[0] for row in db.cursor.fetchall()])
db.close()

print("📊 СРАВНЕНИЕ ТИКЕРОВ")
print("=" * 60)
print()

print(f"📄 В Excel файле: {len(excel_tickers)} тикеров")
print(f"   {sorted(excel_tickers)}")
print()

print(f"💾 В базе данных: {len(db_tickers)} тикеров")
print(f"   {sorted(db_tickers)}")
print()

# Тикеры только в Excel (нет в БД)
only_in_excel = excel_tickers - db_tickers
if only_in_excel:
    print(f"⚠️  Тикеры ТОЛЬКО в Excel (нет данных в БД): {len(only_in_excel)}")
    print(f"   {sorted(only_in_excel)}")
    print("   ⚠️  Для этих тикеров будут использоваться начальные значения ($100, 0%)")
    print()

# Тикеры только в БД (нет в Excel)
only_in_db = db_tickers - excel_tickers
if only_in_db:
    print(f"💡 Тикеры ТОЛЬКО в БД (не в Excel): {len(only_in_db)}")
    print(f"   {sorted(only_in_db)}")
    print("   💡 Эти компании не будут анализироваться")
    print()

# Общие тикеры
common = excel_tickers & db_tickers
if common:
    print(f"✅ Общие тикеры: {len(common)}")
    print(f"   {sorted(common)}")
    print()

print("=" * 60)
print()

if only_in_excel:
    print("🔧 РЕКОМЕНДАЦИЯ:")
    print("   Обновите Excel файл, чтобы использовать тикеры из БД:")
    print("   python sync_excel_with_db.py")
