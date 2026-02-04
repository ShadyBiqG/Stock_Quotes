"""
Модуль для работы с SQLite базой данных
Хранение котировок, результатов анализа и истории
"""

import sqlite3
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с SQLite базой данных"""
    
    def __init__(self, db_path: str = "data/stock_analysis.db"):
        """
        Инициализация подключения к БД
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()
    
    def _connect(self) -> None:
        """Подключение к базе данных"""
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"Подключение к БД: {self.db_path}")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            raise
    
    def _create_tables(self) -> None:
        """Создание таблиц базы данных"""
        
        # Таблица компаний
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                name TEXT,
                description TEXT,
                sector TEXT,
                industry TEXT,
                last_updated TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица котировок
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                price REAL NOT NULL,
                change_percent REAL,
                volume INTEGER,
                additional_info TEXT,
                analysis_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                UNIQUE(company_id, analysis_date)
            )
        """)
        
        # Таблица результатов анализа
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                model_id TEXT NOT NULL,
                prediction TEXT NOT NULL,
                reasons TEXT,
                confidence TEXT,
                raw_response TEXT,
                validation_flags TEXT,
                tokens_used INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stock_id) REFERENCES stocks(id)
            )
        """)
        
        # Таблица консенсуса
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS consensus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_id INTEGER NOT NULL,
                agreed_prediction TEXT,
                disagreement_count INTEGER,
                avg_confidence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stock_id) REFERENCES stocks(id)
            )
        """)
        
        # Таблица истории точности
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS accuracy_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_id INTEGER NOT NULL,
                model_id TEXT NOT NULL,
                predicted TEXT NOT NULL,
                actual TEXT,
                was_correct BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stock_id) REFERENCES stocks(id)
            )
        """)
        
        # Таблица источников цен (v3.0)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stock_id) REFERENCES stocks(id)
            )
        """)
        
        # Создание индексов
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stocks_date 
            ON stocks(analysis_date)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_stock 
            ON analysis_results(stock_id)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_companies_ticker 
            ON companies(ticker)
        """)
        
        self.conn.commit()
        logger.info("Таблицы базы данных созданы/проверены")
    
    def get_or_create_company(self, ticker: str, 
                              name: str = None,
                              description: str = None,
                              sector: str = None,
                              industry: str = None) -> int:
        """
        Получить или создать запись компании
        
        Args:
            ticker: Тикер акции
            name: Название компании
            description: Описание
            sector: Сектор
            industry: Индустрия
            
        Returns:
            ID компании
        """
        # Поиск существующей
        self.cursor.execute(
            "SELECT id FROM companies WHERE ticker = ?",
            (ticker,)
        )
        row = self.cursor.fetchone()
        
        if row:
            company_id = row['id']
            
            # Обновление информации если есть новые данные
            if any([name, description, sector, industry]):
                self._update_company_info(
                    company_id, name, description, sector, industry
                )
            
            return company_id
        
        # Создание новой
        self.cursor.execute("""
            INSERT INTO companies (ticker, name, description, sector, industry, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, name, description, sector, industry, datetime.now()))
        
        self.conn.commit()
        logger.debug(f"Создана компания: {ticker}")
        
        return self.cursor.lastrowid
    
    def _update_company_info(self, company_id: int,
                            name: str = None,
                            description: str = None,
                            sector: str = None,
                            industry: str = None) -> None:
        """Обновление информации о компании"""
        updates = []
        params = []
        
        if name:
            updates.append("name = ?")
            params.append(name)
        if description:
            updates.append("description = ?")
            params.append(description)
        if sector:
            updates.append("sector = ?")
            params.append(sector)
        if industry:
            updates.append("industry = ?")
            params.append(industry)
        
        if updates:
            updates.append("last_updated = ?")
            params.append(datetime.now())
            params.append(company_id)
            
            query = f"UPDATE companies SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, params)
            self.conn.commit()
    
    def save_stock(self, ticker: str, price: float, change: float,
                   volume: int, additional_info: str = "",
                   analysis_date: date = None) -> int:
        """
        Сохранить данные котировки
        
        Args:
            ticker: Тикер акции
            price: Цена
            change: Изменение в %
            volume: Объем
            additional_info: Доп. информация
            analysis_date: Дата анализа (по умолчанию - сегодня)
            
        Returns:
            ID записи котировки
        """
        if analysis_date is None:
            analysis_date = date.today()
        
        # Получить или создать компанию
        company_id = self.get_or_create_company(ticker)
        
        # Проверка существующей записи за эту дату
        self.cursor.execute("""
            SELECT id FROM stocks 
            WHERE company_id = ? AND analysis_date = ?
        """, (company_id, analysis_date))
        
        existing = self.cursor.fetchone()
        
        if existing:
            # Обновление существующей
            stock_id = existing['id']
            self.cursor.execute("""
                UPDATE stocks 
                SET price = ?, change_percent = ?, volume = ?, additional_info = ?
                WHERE id = ?
            """, (price, change, volume, additional_info, stock_id))
            logger.debug(f"Обновлена котировка {ticker} за {analysis_date}")
        else:
            # Создание новой
            self.cursor.execute("""
                INSERT INTO stocks 
                (company_id, price, change_percent, volume, additional_info, analysis_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (company_id, price, change, volume, additional_info, analysis_date))
            stock_id = self.cursor.lastrowid
            logger.debug(f"Создана котировка {ticker} за {analysis_date}")
        
        self.conn.commit()
        return stock_id
    
    def save_price_source(self, stock_id: int, source: str) -> int:
        """
        Сохранить источник цены (v3.0)
        
        Args:
            stock_id: ID котировки
            source: Источник ('yahoo_finance', 'manual', 'default')
            
        Returns:
            ID записи источника
        """
        self.cursor.execute("""
            INSERT INTO price_sources (stock_id, source)
            VALUES (?, ?)
        """, (stock_id, source))
        
        self.conn.commit()
        return self.cursor.lastrowid
    
    def save_analysis(self, stock_id: int, model_name: str, model_id: str,
                      prediction: str, reasons: List[str], confidence: str,
                      raw_response: str, validation_flags: Dict,
                      tokens_used: int = 0) -> int:
        """
        Сохранить результат анализа
        
        Args:
            stock_id: ID котировки
            model_name: Название модели
            model_id: ID модели
            prediction: Прогноз (РАСТЕТ/ПАДАЕТ/СТАБИЛЬНА)
            reasons: Список причин
            confidence: Уверенность (ВЫСОКАЯ/СРЕДНЯЯ/НИЗКАЯ)
            raw_response: Сырой ответ модели
            validation_flags: Флаги валидации
            tokens_used: Использовано токенов
            
        Returns:
            ID записи анализа
        """
        self.cursor.execute("""
            INSERT INTO analysis_results 
            (stock_id, model_name, model_id, prediction, reasons, confidence,
             raw_response, validation_flags, tokens_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stock_id, model_name, model_id, prediction,
            json.dumps(reasons, ensure_ascii=False),
            confidence, raw_response,
            json.dumps(validation_flags, ensure_ascii=False),
            tokens_used
        ))
        
        self.conn.commit()
        return self.cursor.lastrowid
    
    def save_consensus(self, stock_id: int, agreed_prediction: str = None,
                      disagreement_count: int = 0,
                      avg_confidence: str = "СРЕДНЯЯ") -> int:
        """
        Сохранить консенсус моделей
        
        Args:
            stock_id: ID котировки
            agreed_prediction: Согласованный прогноз
            disagreement_count: Количество разногласий
            avg_confidence: Средняя уверенность
            
        Returns:
            ID записи консенсуса
        """
        self.cursor.execute("""
            INSERT INTO consensus 
            (stock_id, agreed_prediction, disagreement_count, avg_confidence)
            VALUES (?, ?, ?, ?)
        """, (stock_id, agreed_prediction, disagreement_count, avg_confidence))
        
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_analysis_results(self, analysis_date: date = None,
                            ticker: str = None) -> List[Dict]:
        """
        Получить результаты анализа
        
        Args:
            analysis_date: Дата анализа (по умолчанию - сегодня)
            ticker: Фильтр по тикеру
            
        Returns:
            Список результатов
        """
        if analysis_date is None:
            analysis_date = date.today()
        
        query = """
            SELECT 
                c.ticker, c.name, c.description, c.sector,
                s.price, s.change_percent, s.volume, s.analysis_date,
                ar.model_name, ar.prediction, ar.reasons, ar.confidence,
                ar.validation_flags, ar.tokens_used
            FROM analysis_results ar
            JOIN stocks s ON ar.stock_id = s.id
            JOIN companies c ON s.company_id = c.id
            WHERE s.analysis_date = ?
        """
        
        params = [analysis_date]
        
        if ticker:
            query += " AND c.ticker = ?"
            params.append(ticker)
        
        query += " ORDER BY c.ticker, ar.model_name"
        
        self.cursor.execute(query, params)
        
        results = []
        for row in self.cursor.fetchall():
            results.append({
                'ticker': row['ticker'],
                'name': row['name'],
                'description': row['description'],
                'sector': row['sector'],
                'price': row['price'],
                'change': row['change_percent'],
                'volume': row['volume'],
                'model_name': row['model_name'],
                'prediction': row['prediction'],
                'reasons': json.loads(row['reasons']) if row['reasons'] else [],
                'confidence': row['confidence'],
                'validation_flags': json.loads(row['validation_flags']) if row['validation_flags'] else {},
                'tokens_used': row['tokens_used']
            })
        
        return results
    
    def get_historical_data(self, ticker: str, days: int = 30) -> List[Dict]:
        """
        Получить исторические данные по акции
        
        Args:
            ticker: Тикер акции
            days: Количество дней истории
            
        Returns:
            Список данных по дням
        """
        query = """
            SELECT 
                s.analysis_date, s.price, s.change_percent,
                ar.model_name, ar.prediction, ar.confidence
            FROM stocks s
            JOIN companies c ON s.company_id = c.id
            LEFT JOIN analysis_results ar ON ar.stock_id = s.id
            WHERE c.ticker = ?
            AND s.analysis_date >= date('now', '-' || ? || ' days')
            ORDER BY s.analysis_date DESC, ar.model_name
        """
        
        self.cursor.execute(query, (ticker, days))
        
        results = []
        for row in self.cursor.fetchall():
            results.append({
                'date': row['analysis_date'],
                'price': row['price'],
                'change': row['change_percent'],
                'model_name': row['model_name'],
                'prediction': row['prediction'],
                'confidence': row['confidence']
            })
        
        return results
    
    def close(self) -> None:
        """Закрыть соединение с БД"""
        if self.conn:
            self.conn.close()
            logger.info("Соединение с БД закрыто")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    with Database() as db:
        # Пример сохранения данных
        stock_id = db.save_stock(
            ticker="AAPL",
            price=150.25,
            change=2.5,
            volume=1000000
        )
        print(f"Сохранена котировка, ID: {stock_id}")
