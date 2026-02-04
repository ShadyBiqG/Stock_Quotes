"""
Создание Excel файла с начальными данными для первого анализа
"""

import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import pandas as pd

# Примерные текущие данные (замените на реальные!)
# Источник: finance.yahoo.com, investing.com и т.д.
initial_data = [
    {'Ticker': 'NVDA',  'Price': 875.28,  'Change': -2.8,  'Volume': 42000000},
    {'Ticker': 'AVGO',  'Price': 1450.50, 'Change': 1.2,   'Volume': 2800000},
    {'Ticker': 'TSM',   'Price': 145.60,  'Change': -0.5,  'Volume': 12000000},
    {'Ticker': 'ASMLF', 'Price': 1025.30, 'Change': 0.8,   'Volume': 450000},
    {'Ticker': 'ASML',  'Price': 1025.30, 'Change': 0.8,   'Volume': 450000},
    {'Ticker': 'MU',    'Price': 88.45,   'Change': -1.2,  'Volume': 18000000},
    {'Ticker': 'AMD',   'Price': 178.90,  'Change': 2.5,   'Volume': 45000000},
    {'Ticker': 'LRCX',  'Price': 825.60,  'Change': -0.3,  'Volume': 1200000},
    {'Ticker': 'AMAT',  'Price': 195.75,  'Change': 1.8,   'Volume': 6500000},
    {'Ticker': 'INTC',  'Price': 42.30,   'Change': -3.5,  'Volume': 52000000},
]

def create_initial_excel():
    """Создание Excel файла с начальными данными"""
    
    print("=" * 80)
    print("📄 СОЗДАНИЕ EXCEL С НАЧАЛЬНЫМИ ДАННЫМИ")
    print("=" * 80)
    print()
    
    df = pd.DataFrame(initial_data)
    
    # Показываем данные
    print("Данные для создания:")
    print(df.to_string(index=False))
    print()
    
    # Сохраняем
    filename = "Stock_quotes_with_data.xlsx"
    df.to_excel(filename, index=False)
    
    print(f"✅ Файл создан: {filename}")
    print()
    print("📋 ИНСТРУКЦИЯ:")
    print("1. Обновите цены в файле реальными данными")
    print("2. Скопируйте файл: copy Stock_quotes_with_data.xlsx Stock_quotes.xlsx")
    print("3. Запустите анализ: start.bat или start_web.bat")
    print("4. После первого анализа можно удалить колонки Price, Change, Volume")
    print("   (данные будут сохранены в БД)")
    print()
    print("=" * 80)


if __name__ == "__main__":
    create_initial_excel()
