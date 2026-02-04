"""
Дашборд "Настройки" - управление анализом, экспорт, конфигурация
"""

import streamlit as st
import yaml
import json
import asyncio
from pathlib import Path
import sys
from datetime import date, datetime
import os
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import load_stock_data, DataLoader
from src.database import Database
from src.llm_manager import OpenRouterClient
from src.company_info import CompanyInfoProvider
from src.analyzer import StockAnalyzer
from src.excel_exporter import ExcelExporter
from src.price_fetcher import YahooFinanceFetcher


def save_company_to_json(ticker: str, company_info: dict) -> bool:
    """
    Сохранение компании в companies.json (v3.0)
    
    Args:
        ticker: Тикер компании
        company_info: Информация о компании
        
    Returns:
        True если успешно, False при ошибке
    """
    try:
        json_path = Path('config/companies.json')
        
        # Создание файла если не существует
        if not json_path.exists():
            json_path.parent.mkdir(parents=True, exist_ok=True)
            data = {'companies': [], 'last_updated': datetime.now().isoformat()}
        else:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # Проверка на дубликат
        if not any(c.get('ticker') == ticker for c in data['companies']):
            data['companies'].append({
                'ticker': ticker,
                'name': company_info.get('name', ''),
                'sector': company_info.get('sector', ''),
                'industry': company_info.get('industry', '')
            })
            data['last_updated'] = datetime.now().isoformat()
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"Ошибка сохранения в companies.json: {e}")
        return False


def remove_company_from_json(ticker: str) -> bool:
    """
    Удаление компании из companies.json (v3.0)
    
    Args:
        ticker: Тикер компании
        
    Returns:
        True если успешно, False при ошибке
    """
    try:
        json_path = Path('config/companies.json')
        
        if not json_path.exists():
            return True
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Удаление компании
        original_count = len(data['companies'])
        data['companies'] = [c for c in data['companies'] if c.get('ticker') != ticker]
        
        if len(data['companies']) < original_count:
            data['last_updated'] = datetime.now().isoformat()
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"Ошибка удаления из companies.json: {e}")
        return False


def export_companies_to_json(db: Database) -> bool:
    """
    Экспорт всех компаний из БД в companies.json (v3.0)
    
    Args:
        db: Экземпляр Database
        
    Returns:
        True если успешно, False при ошибке
    """
    try:
        json_path = Path('config/companies.json')
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Загрузка всех компаний из БД
        db.cursor.execute("SELECT ticker, name, sector, industry FROM companies ORDER BY ticker")
        companies = []
        
        for row in db.cursor.fetchall():
            companies.append({
                'ticker': row['ticker'],
                'name': row['name'] or '',
                'sector': row['sector'] or '',
                'industry': row['industry'] or ''
            })
        
        data = {
            'companies': companies,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        logging.error(f"Ошибка экспорта в companies.json: {e}")
        return False


def show(config: dict):
    """
    Отображение дашборда "Настройки"
    
    Args:
        config: Конфигурация приложения
    """
    st.title("⚙️ Настройки и управление")
    st.markdown("Запуск анализа, экспорт данных и конфигурация")
    
    # Вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚀 Запуск анализа",
        "📥 Экспорт данных",
        "🔧 Конфигурация",
        "📊 Информация"
    ])
    
    # === ВКЛАДКА: ЗАПУСК АНАЛИЗА ===
    with tab1:
        st.markdown("### 🚀 Запуск анализа")
        
        # Загрузка Excel файла
        st.markdown("#### 📂 Загрузка данных")
        
        uploaded_file = st.file_uploader(
            "Выберите Excel файл с котировками",
            type=['xlsx', 'xls'],
            help="Файл должен содержать колонки: Ticker, Price, Change, Volume"
        )
        
        if uploaded_file:
            # Сохранение файла
            save_path = Path("data/samples/Stock quotes.xlsx")
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
            
            st.success(f"✅ Файл загружен: {uploaded_file.name}")
            
            # Предпросмотр данных
            try:
                # Подключение к БД для загрузки котировок
                db_preview = Database(config['database']['path'])
                stocks = load_stock_data(str(save_path), database=db_preview)
                db_preview.close()
                stats = DataLoader.validate_data(stocks)
                
                st.markdown("#### 📊 Предпросмотр данных")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Всего акций", stats['total'])
                
                with col2:
                    st.metric("Растут", stats['growing'])
                
                with col3:
                    st.metric("Падают", stats['falling'])
                
                with col4:
                    st.metric("Стабильны", stats['stable'])
                
                # Список тикеров
                with st.expander("📋 Список тикеров"):
                    st.write(", ".join(stats['tickers']))
                
            except Exception as e:
                st.error(f"❌ Ошибка чтения файла: {e}")
                return
        
        else:
            # Использовать существующий файл
            default_file = Path("data/samples/Stock quotes.xlsx")
            if default_file.exists():
                st.info(f"📁 Используется существующий файл: {default_file}")
                
                try:
                    # Подключение к БД для загрузки котировок
                    db_preview = Database(config['database']['path'])
                    stocks = load_stock_data(str(default_file), database=db_preview)
                    db_preview.close()
                    stats = DataLoader.validate_data(stocks)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Всего акций", stats['total'])
                    
                    with col2:
                        st.metric("Растут", stats['growing'])
                    
                    with col3:
                        st.metric("Падают", stats['falling'])
                    
                    with col4:
                        st.metric("Стабильны", stats['stable'])
                    
                except Exception as e:
                    st.error(f"❌ Ошибка чтения файла: {e}")
                    return
            else:
                st.warning("⚠️ Файл data/samples/Stock quotes.xlsx не найден. Загрузите файл выше.")
                return
        
        st.markdown("---")
        
        # Настройки анализа
        st.markdown("#### ⚙️ Настройки анализа")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_models = st.multiselect(
                "Выберите модели",
                options=[m['name'] for m in config['models']],
                default=[m['name'] for m in config['models']],
                help="Выберите LLM модели для анализа"
            )
        
        with col2:
            max_retries = st.number_input(
                "Макс. попыток при ошибке",
                min_value=1,
                max_value=5,
                value=3
            )
        
        # Проверка API ключа
        api_key = config['openrouter']['api_key']
        
        if not api_key or api_key == "your-openrouter-api-key-here":
            st.error("❌ OpenRouter API ключ не настроен!")
            st.info("💡 Настройте ключ в config.yaml или переменной окружения OPENROUTER_API_KEY")
            
            with st.expander("📝 Как получить API ключ"):
                st.markdown("""
                1. Зарегистрируйтесь на [openrouter.ai](https://openrouter.ai/)
                2. Перейдите в раздел "Keys"
                3. Создайте новый API ключ
                4. Пополните баланс ($10-20 для начала)
                5. Добавьте ключ в config.yaml
                """)
            
            return
        
        st.success(f"✅ API ключ настроен (••••{api_key[-4:]})")
        
        st.markdown("---")
        
        # Кнопка запуска
        st.markdown("#### 🚀 Запуск")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info(f"📊 Будет проанализировано: {stats['total']} акций × {len(selected_models)} моделей")
        
        with col2:
            if st.button("▶️ Запустить анализ", type="primary", use_container_width=True):
                if not selected_models:
                    st.error("Выберите хотя бы одну модель!")
                    return
                
                # Запуск анализа
                run_analysis(config, selected_models, max_retries)
    
    # === ВКЛАДКА: ЭКСПОРТ ДАННЫХ ===
    with tab2:
        st.markdown("### 📥 Экспорт данных")
        
        # Подключение к БД
        try:
            db = Database(config['database']['path'])
        except Exception as e:
            st.error(f"Ошибка подключения к БД: {e}")
            return
        
        # Выбор даты
        col1, col2 = st.columns([2, 1])
        
        with col1:
            export_date = st.date_input(
                "Дата для экспорта",
                value=date.today(),
                max_value=date.today()
            )
        
        with col2:
            st.write("")
            st.write("")
            if st.button("📊 Загрузить данные", use_container_width=True):
                st.rerun()
        
        # Загрузка данных
        results = db.get_analysis_results(analysis_date=export_date)
        
        if not results:
            st.warning(f"⚠️ Нет данных за {export_date}")
        else:
            st.success(f"✅ Найдено {len(results)} записей анализа")
            
            # Предпросмотр
            with st.expander("👁️ Предпросмотр данных"):
                import pandas as pd
                df = pd.DataFrame(results[:10])  # Первые 10
                st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            
            # Экспорт в Excel
            st.markdown("#### 📄 Экспорт в Excel")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                filename = st.text_input(
                    "Имя файла",
                    value=f"{export_date}_analysis.xlsx"
                )
            
            with col2:
                st.write("")
                st.write("")
                if st.button("💾 Создать Excel", type="primary", use_container_width=True):
                    try:
                        exporter = ExcelExporter()
                        filepath = exporter.export(results, export_date, filename)
                        
                        st.success(f"✅ Файл создан: {filepath}")
                        
                        # Скачивание файла
                        with open(filepath, 'rb') as f:
                            st.download_button(
                                label="📥 Скачать Excel",
                                data=f.read(),
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    
                    except Exception as e:
                        st.error(f"❌ Ошибка экспорта: {e}")
        
        db.close()
    
    # === ВКЛАДКА: КОНФИГУРАЦИЯ ===
    with tab3:
        st.markdown("### 🔧 Конфигурация")
        
        # === УПРАВЛЕНИЕ КОМПАНИЯМИ ===
        st.markdown("#### 🏢 Управление компаниями")
        st.info("💡 Добавляйте компании по Ticker - остальная информация будет получена автоматически через LLM")
        
        # Подключение к БД
        try:
            db = Database(config['database']['path'])
        except Exception as e:
            st.error(f"Ошибка подключения к БД: {e}")
            return
        
        # Загрузка существующих компаний
        db.cursor.execute("SELECT * FROM companies ORDER BY ticker")
        companies = [dict(row) for row in db.cursor.fetchall()]
        
        # Добавление новой компании
        with st.expander("➕ Добавить новую компанию", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                new_ticker = st.text_input(
                    "Тикер компании",
                    placeholder="Например: AAPL, GOOGL, MSFT",
                    key="new_ticker"
                ).upper().strip()
            
            with col2:
                st.write("")
                st.write("")
                if st.button("✅ Добавить", use_container_width=True, key="add_company"):
                    if new_ticker:
                        # Проверка на дубликат
                        existing = [c for c in companies if c['ticker'] == new_ticker]
                        if existing:
                            st.error(f"❌ Компания {new_ticker} уже существует!")
                        else:
                            # Получение информации через LLM
                            with st.spinner(f"🔍 Получение информации о {new_ticker}..."):
                                try:
                                    llm_client = OpenRouterClient(
                                        api_key=config['openrouter']['api_key'],
                                        base_url=config['openrouter']['base_url']
                                    )
                                    
                                    company_provider = CompanyInfoProvider(
                                        cache_duration_days=config['company_info']['cache_duration_days'],
                                        fallback_llm_client=llm_client,
                                        alphavantage_api_key=config['company_info'].get('alphavantage_api_key', None)
                                    )
                                    
                                    info = company_provider.get_company_info(new_ticker, use_cache=False)
                                    
                                    # Получение текущей цены через Yahoo Finance (v3.0)
                                    price_fetcher = YahooFinanceFetcher()
                                    price_data = price_fetcher.get_current_price(new_ticker)
                                    
                                    # Сохранение в БД
                                    company_id = db.get_or_create_company(
                                        ticker=new_ticker,
                                        name=info.get('name', ''),
                                        description=info.get('description', ''),
                                        sector=info.get('sector', ''),
                                        industry=info.get('industry', '')
                                    )
                                    
                                    # Сохранение котировки
                                    stock_id = db.save_stock(
                                        ticker=new_ticker,
                                        price=price_data['price'],
                                        change=price_data['change_percent'],
                                        volume=price_data['volume'],
                                        additional_info='',
                                        analysis_date=date.today()
                                    )
                                    
                                    # Сохранение источника цены
                                    db.save_price_source(stock_id, price_data['source'])
                                    
                                    # Автоматическое сохранение в companies.json (v3.0)
                                    if save_company_to_json(new_ticker, info):
                                        st.success(f"✅ Компания {new_ticker} добавлена и сохранена в config/companies.json!")
                                    else:
                                        st.success(f"✅ Компания {new_ticker} добавлена в БД!")
                                        st.warning("⚠️ Не удалось сохранить в companies.json")
                                    
                                    st.info(f"📝 Название: {info.get('name', 'Неизвестно')}")
                                    st.info(f"🏭 Сектор: {info.get('sector', 'Неизвестно')}")
                                    st.info(f"💰 Цена: ${price_data['price']:.2f} ({price_data['change_percent']:+.2f}%)")
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Ошибка добавления: {e}")
                    else:
                        st.warning("⚠️ Введите тикер компании")
        
        st.markdown("---")
        
        # Список компаний с возможностью удаления
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("#### 📋 Список компаний")
        
        with col2:
            # Кнопка экспорта в JSON (v3.0)
            if st.button("📥 Экспорт в JSON", use_container_width=True, help="Экспортировать все компании в config/companies.json"):
                if export_companies_to_json(db):
                    st.success(f"✅ Экспортировано {len(companies)} компаний в config/companies.json")
                else:
                    st.error("❌ Ошибка экспорта")
        
        if companies:
            # Поиск
            search = st.text_input("🔍 Поиск по тикеру или названию", key="search_companies")
            
            filtered_companies = companies
            if search:
                search_lower = search.lower()
                filtered_companies = [
                    c for c in companies 
                    if search_lower in c['ticker'].lower() or 
                       search_lower in (c['name'] or '').lower()
                ]
            
            st.markdown(f"**Найдено компаний:** {len(filtered_companies)}")
            
            # Отображение компаний
            for company in filtered_companies:
                with st.container():
                    col1, col2, col3 = st.columns([2, 4, 1])
                    
                    with col1:
                        st.markdown(f"**{company['ticker']}**")
                    
                    with col2:
                        name = company['name'] or 'Без названия'
                        sector = company['sector'] or 'Неизвестно'
                        st.markdown(f"{name[:40]}... | Сектор: {sector}")
                    
                    with col3:
                        # Кнопка удаления
                        if st.button("🗑️", key=f"del_{company['id']}", help="Удалить компанию и все связанные данные"):
                            try:
                                # Подсчет связанных данных
                                db.cursor.execute(
                                    "SELECT COUNT(*) as cnt FROM stocks WHERE company_id = ?",
                                    (company['id'],)
                                )
                                stock_count = db.cursor.fetchone()['cnt']
                                
                                # Каскадное удаление всех связанных данных
                                if stock_count > 0:
                                    # Получаем ID всех котировок компании
                                    db.cursor.execute(
                                        "SELECT id FROM stocks WHERE company_id = ?",
                                        (company['id'],)
                                    )
                                    stock_ids = [row['id'] for row in db.cursor.fetchall()]
                                    
                                    # Удаляем связанные записи
                                    for stock_id in stock_ids:
                                        # Удаляем историю точности
                                        db.cursor.execute(
                                            "DELETE FROM accuracy_history WHERE stock_id = ?",
                                            (stock_id,)
                                        )
                                        # Удаляем консенсус
                                        db.cursor.execute(
                                            "DELETE FROM consensus WHERE stock_id = ?",
                                            (stock_id,)
                                        )
                                        # Удаляем результаты анализа
                                        db.cursor.execute(
                                            "DELETE FROM analysis_results WHERE stock_id = ?",
                                            (stock_id,)
                                        )
                                    
                                    # Удаляем котировки
                                    db.cursor.execute(
                                        "DELETE FROM stocks WHERE company_id = ?",
                                        (company['id'],)
                                    )
                                
                                # Удаляем саму компанию
                                db.cursor.execute("DELETE FROM companies WHERE id = ?", (company['id'],))
                                db.conn.commit()
                                
                                # Автоматическое удаление из companies.json (v3.0)
                                remove_company_from_json(company['ticker'])
                                
                                st.success(f"✅ Компания {company['ticker']} и все связанные данные ({stock_count} записей) удалены!")
                                st.rerun()
                                
                            except Exception as e:
                                db.conn.rollback()
                                st.error(f"❌ Ошибка удаления: {e}")
                                import traceback
                                logger = logging.getLogger(__name__)
                                logger.error(f"Ошибка удаления компании {company['ticker']}: {traceback.format_exc()}")
                    
                    st.markdown("---")
        else:
            st.info("📝 Нет добавленных компаний. Добавьте первую компанию выше.")
        
        db.close()
        
        st.markdown("---")
        
        # === СИСТЕМНЫЕ НАСТРОЙКИ ===
        st.markdown("#### ⚙️ Системные настройки")
        st.info("💡 Текущие настройки из config.yaml")
        
        # OpenRouter
        with st.expander("🔑 OpenRouter API"):
            st.code(f"API Key: {'•' * 20}{config['openrouter']['api_key'][-4:]}")
            st.code(f"Base URL: {config['openrouter']['base_url']}")
        
        # Модели
        with st.expander("🤖 Модели"):
            for model in config['models']:
                st.markdown(f"**{model['name']}**")
                st.code(f"ID: {model['id']}\nTemperature: {model['temperature']}\nMax tokens: {model['max_tokens']}")
                st.markdown("---")
        
        # База данных
        with st.expander("💾 База данных"):
            st.code(f"Path: {config['database']['path']}")
            
            db_path = Path(config['database']['path'])
            if db_path.exists():
                size_mb = db_path.stat().st_size / 1024 / 1024
                st.info(f"📊 Размер БД: {size_mb:.2f} MB")
        
        # Компания Info
        with st.expander("🏢 Источники информации о компаниях"):
            alphavantage_key = config['company_info'].get('alphavantage_api_key', '')
            if alphavantage_key:
                st.code("Источники: Alphavantage → Yahoo Finance → LLM")
            else:
                st.code("Источники: Yahoo Finance → LLM (рекомендуется)")
            st.code(f"Fallback на LLM: {config['company_info']['fallback_to_llm']}")
            st.code(f"Кэш (дней): {config['company_info']['cache_duration_days']}")
            st.code(f"LLM модель: {config['company_info']['llm_model']}")
        
        st.markdown("---")
        st.warning("⚠️ Для изменения системных настроек отредактируйте файл config.yaml")
    
    # === ВКЛАДКА: ИНФОРМАЦИЯ ===
    with tab4:
        st.markdown("### 📊 Информация о системе")
        
        # Версия Python
        import sys
        st.markdown(f"**Python версия:** {sys.version}")
        
        # Установленные пакеты
        st.markdown("**Ключевые пакеты:**")
        
        packages = {
            'streamlit': st.__version__,
            'pandas': 'Установлен',
            'plotly': 'Установлен',
            'openai': 'Установлен'
        }
        
        for pkg, ver in packages.items():
            st.code(f"{pkg}: {ver}")
        
        st.markdown("---")
        
        # Статистика БД
        st.markdown("### 💾 Статистика базы данных")
        
        try:
            db = Database(config['database']['path'])
            
            # Подсчет записей
            db.cursor.execute("SELECT COUNT(*) FROM companies")
            companies_count = db.cursor.fetchone()[0]
            
            db.cursor.execute("SELECT COUNT(*) FROM stocks")
            stocks_count = db.cursor.fetchone()[0]
            
            db.cursor.execute("SELECT COUNT(*) FROM analysis_results")
            analyses_count = db.cursor.fetchone()[0]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Компаний", companies_count)
            
            with col2:
                st.metric("Котировок", stocks_count)
            
            with col3:
                st.metric("Анализов", analyses_count)
            
            db.close()
            
        except Exception as e:
            st.error(f"Ошибка получения статистики: {e}")


def run_analysis(config: dict, selected_models: list, max_retries: int):
    """
    Запуск анализа
    
    Args:
        config: Конфигурация
        selected_models: Список выбранных моделей
        max_retries: Макс. попыток
    """
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Инициализация БД сначала
        db = Database(config['database']['path'])
        
        # Загрузка данных
        status_text.text("📂 Загрузка данных...")
        stocks = load_stock_data("data/samples/Stock quotes.xlsx", database=db)
        progress_bar.progress(10)
        
        # Фильтрация моделей
        models = [m for m in config['models'] if m['name'] in selected_models]
        config_copy = config.copy()
        config_copy['models'] = models
        
        # Инициализация компонентов
        status_text.text("🔧 Инициализация компонентов...")
        
        llm_client = OpenRouterClient(
            api_key=config['openrouter']['api_key'],
            base_url=config['openrouter']['base_url']
        )
        progress_bar.progress(30)
        
        alphavantage_key = config['company_info'].get('alphavantage_api_key', '')
        company_provider = CompanyInfoProvider(
            cache_duration_days=config['company_info']['cache_duration_days'],
            fallback_llm_client=llm_client if config['company_info']['fallback_to_llm'] else None,
            alphavantage_api_key=alphavantage_key if alphavantage_key else None
        )
        progress_bar.progress(40)
        
        analyzer = StockAnalyzer(
            llm_client=llm_client,
            database=db,
            company_provider=company_provider,
            config=config_copy
        )
        progress_bar.progress(50)
        
        # Запуск анализа
        status_text.text("🚀 Запуск анализа...")
        
        # Streamlit не поддерживает asyncio напрямую, используем синхронный подход
        import nest_asyncio
        nest_asyncio.apply()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        stats = loop.run_until_complete(
            analyzer.analyze_stocks(stocks, date.today(), max_retries)
        )
        
        progress_bar.progress(90)
        
        # Экспорт
        status_text.text("📄 Создание отчета...")
        results = db.get_analysis_results(analysis_date=date.today())
        
        exporter = ExcelExporter()
        export_path = exporter.export(results, date.today())
        
        progress_bar.progress(100)
        
        # Результаты
        status_text.empty()
        progress_bar.empty()
        
        st.success("✅ Анализ завершен успешно!")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Успешно", stats['successful'])
        
        with col2:
            st.metric("Ошибок", stats['failed'])
        
        with col3:
            st.metric("Время", f"{stats['execution_time']:.1f}с")
        
        # Скачивание отчета
        with open(export_path, 'rb') as f:
            st.download_button(
                label="📥 Скачать отчет",
                data=f.read(),
                file_name=export_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        db.close()
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Ошибка анализа: {e}")
        import traceback
        with st.expander("🔍 Подробности ошибки"):
            st.code(traceback.format_exc())
