"""
Скрипт для обновления Excel файла - оставляем только колонку Ticker
Все остальные данные будут храниться в БД
"""

import sys
import codecs

# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import pandas as pd
from pathlib import Path

def update_excel_file(filepath: str = "Stock quotes.xlsx"):
    """
    Обновление Excel файла - оставить только колонку Ticker
    
    Args:
        filepath: Путь к Excel файлу
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        print(f"❌ Файл {filepath} не найден!")
        return
    
    # Читаем существующий файл
    df = pd.read_excel(filepath)
    print(f"📂 Загружен файл: {filepath}")
    print(f"   Текущие колонки: {df.columns.tolist()}")
    print(f"   Строк: {len(df)}")
    
    # Проверяем наличие колонки Ticker
    if 'Ticker' not in df.columns:
        print("❌ Колонка 'Ticker' не найдена!")
        return
    
    # Оставляем только колонку Ticker
    df_new = df[['Ticker']].copy()
    
    # Удаляем пустые строки
    df_new = df_new.dropna(subset=['Ticker'])
    
    # Удаляем дубликаты
    duplicates = df_new.duplicated(subset=['Ticker'], keep='first')
    if duplicates.any():
        print(f"⚠️  Найдено {duplicates.sum()} дубликатов тикеров, удаляем...")
        df_new = df_new.drop_duplicates(subset=['Ticker'], keep='first')
    
    # Создаем резервную копию
    backup_path = filepath.parent / (filepath.stem + "_backup" + filepath.suffix)
    df.to_excel(backup_path, index=False)
    print(f"💾 Создана резервная копия: {backup_path}")
    
    # Сохраняем новый файл
    df_new.to_excel(filepath, index=False)
    
    print(f"✅ Файл обновлен!")
    print(f"   Новые колонки: {df_new.columns.tolist()}")
    print(f"   Строк: {len(df_new)}")
    print(f"   Тикеры: {', '.join(df_new['Ticker'].tolist())}")
    print()
    print("📊 Теперь все данные о котировках будут браться из базы данных.")
    print("   Excel файл используется только для списка анализируемых компаний.")


if __name__ == "__main__":
    update_excel_file("Stock quotes.xlsx")
