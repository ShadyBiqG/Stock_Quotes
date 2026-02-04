"""
Проверка сырого ответа от gpt-5-mini
"""

import sqlite3
import sys

# Исправление кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

conn = sqlite3.connect('data/stocks.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT model_name, raw_response 
    FROM analysis_results 
    WHERE model_name="gpt-5-mini" 
    ORDER BY created_at DESC 
    LIMIT 1
''')

row = cursor.fetchone()

if row:
    print(f"Модель: {row[0]}")
    print(f"\nДлина ответа: {len(row[1])} символов")
    print(f"\nСырой ответ:")
    print("="*80)
    print(row[1])
    print("="*80)
else:
    print("Ответов от gpt-5-mini не найдено")

conn.close()
