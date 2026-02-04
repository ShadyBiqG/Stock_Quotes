"""
Загрузчик данных из Excel файла с котировками акций
Excel файл содержит только список тикеров, данные о котировках берутся из БД
"""

import pandas as pd
from typing import List, Dict, Optional
import logging
from pathlib import Path
from datetime import date

logger = logging.getLogger(__name__)


class DataLoader:
    """Класс для загрузки и валидации данных из Excel файла"""
    
    def __init__(self, filepath: str, database=None):
        """
        Инициализация загрузчика данных
        
        Args:
            filepath: Путь к Excel файлу с тикерами
            database: Экземпляр Database для загрузки котировок из БД
        """
        self.filepath = Path(filepath)
        self.database = database
        if not self.filepath.exists():
            raise FileNotFoundError(f"Файл не найден: {filepath}")
    
    def load(self) -> List[Dict]:
        """
        Загрузка данных из Excel файла
        
        Returns:
            Список словарей с данными по акциям
        """
        logger.info(f"Загрузка данных из {self.filepath}")
        
        try:
            # Чтение Excel файла
            df = pd.read_excel(self.filepath)
            logger.info(f"Загружено {len(df)} строк")
            
            # Валидация обязательных колонок
            self._validate_columns(df)
            
            # Парсинг и валидация данных
            stocks = self._parse_stocks(df)
            
            logger.info(f"Успешно обработано {len(stocks)} акций")
            return stocks
            
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            raise
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Проверка наличия обязательных колонок
        
        Args:
            df: DataFrame с данными
        """
        required_columns = ['Ticker']
        missing = [col for col in required_columns if col not in df.columns]
        
        if missing:
            raise ValueError(
                f"Отсутствуют обязательные колонки: {', '.join(missing)}\n"
                f"Доступные колонки: {', '.join(df.columns)}"
            )
        
        logger.debug("Все обязательные колонки присутствуют")
    
    def _parse_stocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Парсинг данных по акциям
        
        Args:
            df: DataFrame с данными
            
        Returns:
            Список словарей с данными по акциям
        """
        stocks = []
        
        for idx, row in df.iterrows():
            try:
                stock = self._parse_stock_row(row, idx)
                if stock:
                    stocks.append(stock)
            except Exception as e:
                logger.warning(f"Ошибка обработки строки {idx}: {e}")
                continue
        
        return stocks
    
    def _parse_stock_row(self, row: pd.Series, idx: int) -> Optional[Dict]:
        """
        Парсинг одной строки с данными акции
        Данные о котировках берутся из БД, если она подключена
        
        Args:
            row: Строка данных
            idx: Индекс строки
            
        Returns:
            Словарь с данными акции или None если данные некорректны
        """
        # Проверка на пустые значения
        if pd.isna(row['Ticker']):
            logger.warning(f"Строка {idx}: пропущен тикер")
            return None
        
        # Парсинг тикера
        ticker = str(row['Ticker']).strip().upper()
        
        # Если БД подключена, пытаемся получить данные оттуда
        if self.database:
            try:
                # Получаем последнюю котировку из БД
                self.database.cursor.execute("""
                    SELECT s.price, s.change_percent, s.volume, s.additional_info
                    FROM stocks s
                    JOIN companies c ON s.company_id = c.id
                    WHERE c.ticker = ?
                    ORDER BY s.analysis_date DESC, s.created_at DESC
                    LIMIT 1
                """, (ticker,))
                
                db_row = self.database.cursor.fetchone()
                
                if db_row:
                    stock = {
                        'ticker': ticker,
                        'price': float(db_row['price']) if db_row['price'] else 100.0,
                        'change': float(db_row['change_percent']) if db_row['change_percent'] else 0.0,
                        'volume': int(db_row['volume']) if db_row['volume'] else 0,
                        'additional_info': db_row['additional_info'] or '',
                        'row_index': idx
                    }
                    logger.debug(f"Загружена акция {ticker} из БД: ${stock['price']}, {stock['change']:+.2f}%")
                    return stock
                else:
                    # Данных в БД нет - создаем заглушку для первого анализа
                    logger.info(f"Акция {ticker} не найдена в БД, создаем запись с начальными значениями")
                    stock = {
                        'ticker': ticker,
                        'price': 100.0,  # Начальная цена
                        'change': 0.0,
                        'volume': 0,
                        'additional_info': '',
                        'row_index': idx
                    }
                    return stock
                    
            except Exception as e:
                logger.warning(f"Ошибка загрузки данных для {ticker} из БД: {e}")
        
        # Если БД не подключена или старый формат с колонками Price, Change, Volume
        try:
            if 'Price' in row and not pd.isna(row['Price']):
                price = float(row['Price'])
                change = float(row['Change']) if 'Change' in row and not pd.isna(row['Change']) else 0.0
                volume = int(row['Volume']) if 'Volume' in row and not pd.isna(row['Volume']) else 0
                additional_info = str(row['Info']).strip() if 'Info' in row and not pd.isna(row['Info']) else ''
                
                if price <= 0:
                    logger.warning(f"Строка {idx}: некорректная цена {price}")
                    return None
            else:
                # Начальные значения для первого запуска
                price = 100.0
                change = 0.0
                volume = 0
                additional_info = ''
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Строка {idx}: ошибка преобразования типов - {e}")
            # Используем значения по умолчанию
            price = 100.0
            change = 0.0
            volume = 0
            additional_info = ''
        
        stock = {
            'ticker': ticker,
            'price': price,
            'change': change,
            'volume': volume,
            'additional_info': additional_info,
            'row_index': idx
        }
        
        logger.debug(f"Обработана акция: {ticker} (${price}, {change:+.2f}%)")
        return stock
    
    @staticmethod
    def validate_data(stocks: List[Dict]) -> Dict:
        """
        Статистика по загруженным данным
        
        Args:
            stocks: Список данных по акциям
            
        Returns:
            Словарь со статистикой
        """
        if not stocks:
            return {
                'total': 0,
                'growing': 0,
                'falling': 0,
                'stable': 0
            }
        
        stats = {
            'total': len(stocks),
            'growing': sum(1 for s in stocks if s['change'] > 0.5),
            'falling': sum(1 for s in stocks if s['change'] < -0.5),
            'stable': sum(1 for s in stocks if -0.5 <= s['change'] <= 0.5),
            'avg_price': sum(s['price'] for s in stocks) / len(stocks),
            'avg_change': sum(s['change'] for s in stocks) / len(stocks),
            'tickers': [s['ticker'] for s in stocks]
        }
        
        return stats


def load_stock_data(filepath: str, database=None) -> List[Dict]:
    """
    Удобная функция для загрузки данных
    
    Args:
        filepath: Путь к Excel файлу с тикерами
        database: Экземпляр Database для загрузки котировок из БД
        
    Returns:
        Список словарей с данными по акциям
    """
    loader = DataLoader(filepath, database=database)
    return loader.load()


# Пример использования
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Загрузка данных
    try:
        stocks = load_stock_data("Stock quotes.xlsx")
        stats = DataLoader.validate_data(stocks)
        
        print(f"\n📊 Статистика загруженных данных:")
        print(f"  Всего акций: {stats['total']}")
        print(f"  Растут: {stats['growing']} ({stats['growing']/stats['total']*100:.1f}%)")
        print(f"  Падают: {stats['falling']} ({stats['falling']/stats['total']*100:.1f}%)")
        print(f"  Стабильны: {stats['stable']} ({stats['stable']/stats['total']*100:.1f}%)")
        print(f"  Средняя цена: ${stats['avg_price']:.2f}")
        print(f"  Среднее изменение: {stats['avg_change']:+.2f}%")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
