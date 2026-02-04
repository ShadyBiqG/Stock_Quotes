"""
Тестовый скрипт для проверки загрузки котировок через Yahoo Finance
"""

import sys
from pathlib import Path
import logging

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import DataLoader
from src.database import Database
from src.price_fetcher import YahooFinanceFetcher

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Тестирование загрузки котировок"""
    print("\n" + "="*60)
    print("ТЕСТ ЗАГРУЗКИ КОТИРОВОК")
    print("="*60 + "\n")
    
    # Инициализация компонентов
    print("[1/4] Инициализация базы данных...")
    db = Database('data/stocks.db')
    print("      [OK] База данных подключена\n")
    
    print("[2/4] Инициализация Yahoo Finance Fetcher...")
    price_fetcher = YahooFinanceFetcher()
    print("      [OK] Fetcher готов\n")
    
    # Загрузка данных
    companies_file = 'config/companies.json'
    print(f"[3/4] Загрузка компаний из {companies_file}...")
    
    if not Path(companies_file).exists():
        print(f"      [X] Файл {companies_file} не найден!")
        return
    
    loader = DataLoader(companies_file, database=db, price_fetcher=price_fetcher)
    stocks = loader.load()
    
    print(f"      [OK] Загружено {len(stocks)} компаний\n")
    
    # Вывод результатов
    print("[4/4] Результаты загрузки:\n")
    print(f"{'Тикер':<10} {'Цена':<12} {'Изменение':<12} {'Объем':<15}")
    print("-" * 60)
    
    for stock in stocks[:10]:  # Показать первые 10
        ticker = stock['ticker']
        price = stock['price']
        change = stock['change']
        volume = stock['volume']
        
        print(f"{ticker:<10} ${price:<11.2f} {change:>+6.2f}%     {volume:>12,}")
    
    if len(stocks) > 10:
        print(f"\n... и еще {len(stocks) - 10} компаний")
    
    # Статистика
    print("\n" + "="*60)
    print("СТАТИСТИКА")
    print("="*60)
    
    stats = DataLoader.validate_data(stocks)
    print(f"\nВсего акций:     {stats['total']}")
    print(f"Растут:          {stats['growing']} ({stats['growing']/stats['total']*100:.1f}%)")
    print(f"Падают:          {stats['falling']} ({stats['falling']/stats['total']*100:.1f}%)")
    print(f"Стабильны:       {stats['stable']} ({stats['stable']/stats['total']*100:.1f}%)")
    print(f"\nСредняя цена:    ${stats['avg_price']:.2f}")
    print(f"Среднее изм.:    {stats['avg_change']:+.2f}%")
    
    # Проверка дефолтных значений
    default_count = sum(1 for s in stocks if s['price'] == 100.0 and s['change'] == 0.0)
    if default_count > 0:
        print(f"\n[!] ВНИМАНИЕ: {default_count} компаний имеют дефолтные значения (цена=$100, изм.=0%)")
        print("    Это может означать, что котировки не были получены через Yahoo Finance")
        print("\n    Компании с дефолтными значениями:")
        for stock in stocks:
            if stock['price'] == 100.0 and stock['change'] == 0.0:
                print(f"    - {stock['ticker']}")
    else:
        print("\n[OK] Все компании имеют реальные котировки!")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        print(f"\n[X] ОШИБКА: {e}\n")
