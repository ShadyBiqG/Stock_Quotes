"""
Проверка текущих данных в БД
"""

import sys
from pathlib import Path
import sqlite3
from datetime import date

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("\n" + "="*60)
    print("ПРОВЕРКА ДАННЫХ В БАЗЕ ДАННЫХ")
    print("="*60 + "\n")
    
    conn = sqlite3.connect('data/stocks.db', detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Проверка котировок
    print("[1] Котировки в таблице stocks:\n")
    c.execute("""
        SELECT c.ticker, c.name, s.price, s.change_percent, s.volume, 
               s.analysis_date, s.created_at
        FROM stocks s
        JOIN companies c ON s.company_id = c.id
        ORDER BY s.analysis_date DESC, c.ticker
        LIMIT 20
    """)
    
    rows = c.fetchall()
    if rows:
        print(f"{'Тикер':<8} {'Цена':<12} {'Изм.%':<10} {'Дата':<12} {'Создано'}")
        print("-" * 70)
        for row in rows:
            print(f"{row['ticker']:<8} ${row['price']:<11.2f} {row['change_percent']:>+6.2f}%   "
                  f"{row['analysis_date']}  {str(row['created_at'])[:19]}")
    else:
        print("  Нет данных")
    
    # Проверка источников
    print("\n[2] Источники котировок (price_sources):\n")
    c.execute("""
        SELECT ps.source, COUNT(*) as count
        FROM price_sources ps
        GROUP BY ps.source
    """)
    
    sources = c.fetchall()
    if sources:
        for row in sources:
            print(f"  {row['source']}: {row['count']} записей")
    else:
        print("  Нет данных об источниках")
    
    # Проверка последних анализов
    print("\n[3] Результаты анализов (analysis_results):\n")
    c.execute("""
        SELECT COUNT(DISTINCT ar.stock_id) as stocks_count,
               COUNT(*) as total_analyses,
               MAX(ar.created_at) as last_analysis
        FROM analysis_results ar
    """)
    
    row = c.fetchone()
    if row and row['total_analyses']:
        print(f"  Проанализировано акций: {row['stocks_count']}")
        print(f"  Всего анализов: {row['total_analyses']}")
        print(f"  Последний анализ: {row['last_analysis']}")
    else:
        print("  Анализов еще не было")
    
    # Проверка дат
    print("\n[4] Даты котировок:\n")
    c.execute("""
        SELECT DISTINCT analysis_date, COUNT(*) as count
        FROM stocks
        GROUP BY analysis_date
        ORDER BY analysis_date DESC
    """)
    
    dates = c.fetchall()
    if dates:
        today = date.today()
        for row in dates:
            date_str = str(row['analysis_date'])
            is_today = " <- СЕГОДНЯ" if str(row['analysis_date']) == str(today) else ""
            print(f"  {date_str}: {row['count']} котировок{is_today}")
    else:
        print("  Нет данных")
    
    print("\n" + "="*60)
    print("РЕКОМЕНДАЦИИ:")
    print("="*60)
    
    if not rows:
        print("\n⚠️  БД пустая! Запустите анализ через:")
        print("   - Веб-интерфейс: кнопка '🚀 Запустить анализ'")
        print("   - CLI: python main.py")
    elif any(row['price'] == 100.0 and row['change_percent'] == 0.0 for row in rows):
        print("\n⚠️  Обнаружены дефолтные значения ($100, 0%)!")
        print("   Это данные ДО миграции на v3.0 или без Yahoo Finance.")
        print("\n   Решение:")
        print("   1. Запустите новый анализ: python main.py")
        print("   2. Или очистите старые данные: DELETE FROM stocks WHERE price = 100.0")
    else:
        print("\n✅ Все котировки выглядят реальными!")
        print(f"   Последнее обновление: {rows[0]['created_at']}")
    
    print("\n" + "="*60 + "\n")
    
    conn.close()

if __name__ == "__main__":
    main()
