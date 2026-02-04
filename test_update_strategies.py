"""
Тестовый скрипт для проверки стратегий обновления котировок
"""

import sys
from pathlib import Path
import logging
import yaml

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

def load_config():
    """Загрузка конфигурации"""
    config_path = Path("config/llm_config.yaml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

def test_strategy(strategy_name: str, config: dict):
    """Тестирование конкретной стратегии"""
    print(f"\n{'='*60}")
    print(f"ТЕСТ СТРАТЕГИИ: {strategy_name}")
    print("="*60)
    
    # Обновляем конфигурацию
    if 'price_updates' not in config:
        config['price_updates'] = {}
    config['price_updates']['strategy'] = strategy_name
    
    # Инициализация компонентов
    db = Database('data/stocks.db')
    price_fetcher = YahooFinanceFetcher()
    
    # Загрузка данных
    companies_file = 'config/companies.json'
    loader = DataLoader(companies_file, database=db, price_fetcher=price_fetcher, config=config)
    
    import time
    start_time = time.time()
    stocks = loader.load()
    elapsed_time = time.time() - start_time
    
    print(f"\n[OK] Загружено {len(stocks)} компаний за {elapsed_time:.2f} сек")
    
    # Показываем первые 3 компании
    print(f"\nПримеры котировок:")
    for stock in stocks[:3]:
        print(f"  {stock['ticker']:<6} ${stock['price']:>8.2f}  {stock['change']:>+6.2f}%")
    
    return elapsed_time

def main():
    """Главная функция"""
    print("\n" + "="*60)
    print("СРАВНЕНИЕ СТРАТЕГИЙ ОБНОВЛЕНИЯ КОТИРОВОК")
    print("="*60)
    
    config = load_config()
    
    strategies = [
        ("cache_only", "Только кэш (самое быстрое)"),
        ("daily", "Раз в день (рекомендуется)"),
        ("always", "Всегда обновлять (самое медленное)")
    ]
    
    results = {}
    
    for strategy_name, description in strategies:
        print(f"\n\n📊 {description}")
        try:
            elapsed = test_strategy(strategy_name, config.copy())
            results[strategy_name] = elapsed
        except Exception as e:
            logger.error(f"Ошибка при тестировании {strategy_name}: {e}")
            results[strategy_name] = None
    
    # Итоговая таблица
    print("\n\n" + "="*60)
    print("ИТОГОВАЯ ТАБЛИЦА")
    print("="*60)
    print(f"\n{'Стратегия':<20} {'Время':<15} {'Описание'}")
    print("-" * 60)
    
    for strategy_name, description in strategies:
        elapsed = results.get(strategy_name)
        if elapsed:
            time_str = f"{elapsed:.2f} сек"
        else:
            time_str = "Ошибка"
        print(f"{strategy_name:<20} {time_str:<15} {description}")
    
    # Рекомендация
    print("\n" + "="*60)
    print("💡 РЕКОМЕНДАЦИИ:")
    print("="*60)
    print("""
1. cache_only - для разработки и отладки (самое быстрое)
2. daily - для продакшена (оптимальный баланс скорости и актуальности)
3. always - если нужны актуальные котировки каждый раз (медленно)

Текущая настройка в config/llm_config.yaml:
  strategy: "{}"
    """.format(config.get('price_updates', {}).get('strategy', 'daily')))
    
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        print(f"\n[X] ОШИБКА: {e}\n")
