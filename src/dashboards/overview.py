"""
Дашборд "Обзор" - главная страница с метриками и последними результатами
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path
import asyncio
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database
from src.data_loader import DataLoader
from src.llm_manager import OpenRouterClient
from src.company_info import CompanyInfoProvider
from src.analyzer import StockAnalyzer
from src.excel_exporter import ExcelExporter


def show(config: dict):
    """
    Отображение дашборда "Обзор"
    
    Args:
        config: Конфигурация приложения
    """
    st.title("🏠 Обзор")
    st.markdown("Последние результаты анализа котировок")
    
    # === БЫСТРЫЕ ДЕЙСТВИЯ ===
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 3])
    
    with col_btn1:
        if st.button("🚀 Запустить анализ", use_container_width=True, type="primary"):
            _run_analysis(config)
    
    with col_btn2:
        if st.button("📥 Экспорт в Excel", use_container_width=True):
            _export_to_excel(config)
    
    with col_btn3:
        st.markdown("")  # Пустое место
    
    st.markdown("---")
    
    # Подключение к БД
    try:
        db = Database(config['database']['path'])
    except Exception as e:
        st.error(f"Ошибка подключения к БД: {e}")
        return
    
    # Выбор даты
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_date = st.date_input(
            "Дата анализа",
            value=date.today(),
            max_value=date.today()
        )
    
    with col2:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()
    
    # Загрузка данных
    results = db.get_analysis_results(analysis_date=selected_date)
    
    if not results:
        st.warning(f"⚠️ Нет данных за {selected_date}")
        st.info("💡 Запустите анализ через меню 'Настройки' или выполните `python main.py`")
        return
    
    # Группировка по тикерам
    stocks_data = {}
    for r in results:
        ticker = r['ticker']
        if ticker not in stocks_data:
            stocks_data[ticker] = {
                'ticker': ticker,
                'name': r.get('name', ''),
                'price': r['price'],
                'change': r['change'],
                'predictions': []
            }
        stocks_data[ticker]['predictions'].append(r['prediction'])
    
    # Консенсус прогнозов
    for ticker, data in stocks_data.items():
        predictions = data['predictions']
        if predictions:
            # Большинство голосов
            most_common = max(set(predictions), key=predictions.count)
            data['consensus'] = most_common
            data['agreement'] = predictions.count(most_common) / len(predictions) * 100
        else:
            data['consensus'] = 'Н/Д'
            data['agreement'] = 0
    
    # Метрики
    st.markdown("### 📊 Ключевые метрики")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Всего акций",
            len(stocks_data),
            delta=None
        )
    
    growing = sum(1 for s in stocks_data.values() if s['consensus'] == 'РАСТЕТ')
    total_stocks = len(stocks_data)
    with col2:
        st.metric(
            "Растут",
            growing,
            delta=f"{growing/total_stocks*100:.0f}%" if total_stocks > 0 else "0%"
        )
    
    falling = sum(1 for s in stocks_data.values() if s['consensus'] == 'ПАДАЕТ')
    with col3:
        st.metric(
            "Падают",
            falling,
            delta=f"-{falling/total_stocks*100:.0f}%" if total_stocks > 0 else "0%",
            delta_color="inverse"
        )
    
    avg_agreement = sum(s['agreement'] for s in stocks_data.values()) / total_stocks if total_stocks > 0 else 0
    with col4:
        st.metric(
            "Консенсус",
            f"{avg_agreement:.0f}%",
            delta="согласие моделей"
        )
    
    # График распределения прогнозов
    st.markdown("### 📈 Распределение прогнозов")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Pie chart
        prediction_counts = {
            'Растут': growing,
            'Падают': falling,
            'Стабильны': sum(1 for s in stocks_data.values() if s['consensus'] == 'СТАБИЛЬНА')
        }
        
        fig = px.pie(
            values=list(prediction_counts.values()),
            names=list(prediction_counts.keys()),
            color=list(prediction_counts.keys()),
            color_discrete_map={
                'Растут': '#90EE90',
                'Падают': '#FFB6C1',
                'Стабильны': '#FFD700'
            },
            hole=0.4
        )
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Статистика")
        st.markdown(f"**Дата:** {selected_date}")
        models_count = len(results) // len(stocks_data) if len(stocks_data) > 0 else 0
        st.markdown(f"**Моделей:** {models_count}")
        st.markdown(f"**Всего анализов:** {len(results)}")
        
        # Средние значения
        total_stocks = len(stocks_data)
        avg_price = sum(s['price'] for s in stocks_data.values()) / total_stocks if total_stocks > 0 else 0
        avg_change = sum(s['change'] for s in stocks_data.values()) / total_stocks if total_stocks > 0 else 0
        
        st.markdown(f"**Ср. цена:** ${avg_price:.2f}")
        st.markdown(f"**Ср. изм.:** {avg_change:+.2f}%")
    
    # Топ акций
    st.markdown("### 🔝 Топ акций")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🟢 Топ-5 роста")
        top_growing = sorted(
            stocks_data.values(),
            key=lambda x: x['change'],
            reverse=True
        )[:5]
        
        for stock in top_growing:
            with st.container():
                st.markdown(f"""
                **{stock['ticker']}** - {stock['name'][:30]}...  
                📈 {stock['change']:+.2f}% | ${stock['price']:.2f}  
                Прогноз: {stock['consensus']} ({stock['agreement']:.0f}% согласие)
                """)
                st.markdown("---")
    
    with col2:
        st.markdown("#### 🔴 Топ-5 падения")
        top_falling = sorted(
            stocks_data.values(),
            key=lambda x: x['change']
        )[:5]
        
        for stock in top_falling:
            with st.container():
                st.markdown(f"""
                **{stock['ticker']}** - {stock['name'][:30]}...  
                📉 {stock['change']:+.2f}% | ${stock['price']:.2f}  
                Прогноз: {stock['consensus']} ({stock['agreement']:.0f}% согласие)
                """)
                st.markdown("---")
    
    # Таблица всех акций
    st.markdown("### 📋 Все акции")
    
    # Подготовка данных для таблицы
    table_data = []
    for stock in stocks_data.values():
        table_data.append({
            'Тикер': stock['ticker'],
            'Название': stock['name'][:40] + '...' if len(stock['name']) > 40 else stock['name'],
            'Цена': f"${stock['price']:.2f}",
            'Изм.%': f"{stock['change']:+.2f}%",
            'Прогноз': stock['consensus'],
            'Согласие': f"{stock['agreement']:.0f}%"
        })
    
    df = pd.DataFrame(table_data)
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_prediction = st.selectbox(
            "Фильтр по прогнозу",
            ["Все", "РАСТЕТ", "ПАДАЕТ", "СТАБИЛЬНА"]
        )
    
    with col2:
        filter_agreement = st.slider(
            "Мин. согласие моделей (%)",
            0, 100, 0
        )
    
    with col3:
        search_ticker = st.text_input("Поиск по тикеру")
    
    # Применение фильтров
    filtered_data = table_data.copy()
    
    if filter_prediction != "Все":
        filtered_data = [d for d in filtered_data if d['Прогноз'] == filter_prediction]
    
    if filter_agreement > 0:
        filtered_data = [
            d for d in filtered_data 
            if float(d['Согласие'].rstrip('%')) >= filter_agreement
        ]
    
    if search_ticker:
        filtered_data = [
            d for d in filtered_data 
            if search_ticker.upper() in d['Тикер'].upper()
        ]
    
    if filtered_data:
        df_filtered = pd.DataFrame(filtered_data)
        
        # Цветовое кодирование через styling
        def color_prediction(val):
            if val == 'РАСТЕТ':
                return 'background-color: #90EE90'
            elif val == 'ПАДАЕТ':
                return 'background-color: #FFB6C1'
            elif val == 'СТАБИЛЬНА':
                return 'background-color: #FFD700'
            return ''
        
        styled_df = df_filtered.style.map(
            color_prediction,
            subset=['Прогноз']
        )
        
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # Экспорт
        if st.button("📥 Скачать таблицу (CSV)"):
            csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="💾 Сохранить CSV",
                data=csv,
                file_name=f"stocks_overview_{selected_date}.csv",
                mime="text/csv"
            )
    else:
        st.info("Нет данных, соответствующих фильтрам")


def _run_analysis(config: dict):
    """
    Запуск анализа с главной страницы
    
    Args:
        config: Конфигурация приложения
    """
    with st.spinner("⏳ Запуск анализа..."):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Инициализация компонентов
            status_text.text("🔧 Инициализация компонентов...")
            
            llm_client = OpenRouterClient(
                api_key=config['openrouter']['api_key'],
                base_url=config['openrouter']['base_url']
            )
            progress_bar.progress(10)
            
            db = Database(config['database']['path'])
            progress_bar.progress(20)
            
            # Price Fetcher (v3.0)
            from src.price_fetcher import YahooFinanceFetcher
            price_fetcher = YahooFinanceFetcher()
            progress_bar.progress(25)
            
            # Проверка файла (v3.0: используем путь из конфигурации)
            excel_file = config.get('input', {}).get('excel_file', 'data/samples/Stock quotes.xlsx')
            if not os.path.exists(excel_file):
                st.error(f"❌ Файл {excel_file} не найден!")
                return
            
            # Загрузка данных (v3.0: с database, price_fetcher и config)
            status_text.text("📂 Загрузка данных...")
            loader = DataLoader(excel_file, database=db, price_fetcher=price_fetcher, config=config)
            stocks = loader.load()
            progress_bar.progress(30)
            
            if not stocks:
                st.error("❌ Не удалось загрузить данные из файла!")
                return
            
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
                config=config
            )
            progress_bar.progress(50)
            
            # Запуск анализа
            status_text.text(f"🚀 Анализ {len(stocks)} акций...")
            
            # Streamlit не поддерживает asyncio напрямую
            import nest_asyncio
            nest_asyncio.apply()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            stats = loop.run_until_complete(
                analyzer.analyze_stocks(stocks, date.today(), max_retries=3)
            )
            
            progress_bar.progress(90)
            
            # Экспорт
            status_text.text("📄 Создание Excel отчета...")
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
                st.metric("✅ Успешно", stats['successful'])
            
            with col2:
                st.metric("❌ Ошибок", stats['failed'])
            
            with col3:
                st.metric("⏱️ Время", f"{stats['execution_time']:.1f}с")
            
            st.info(f"📁 Отчет сохранен: {export_path}")
            
            # Автообновление страницы
            st.balloons()
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Ошибка при анализе: {e}")
            import traceback
            with st.expander("🔍 Подробности ошибки"):
                st.code(traceback.format_exc())


def _export_to_excel(config: dict):
    """
    Экспорт последних результатов в Excel (упрощённый формат).
    
    Формат: Тикер | Компания | Описание | Ответы ИИ (по колонкам) | Итог
    Второй лист: история изменения цены за месяц.
    
    Args:
        config: Конфигурация приложения
    """
    db = None
    try:
        db = Database(config['database']['path'])
        
        # Получаем последние результаты
        results = db.get_analysis_results(analysis_date=date.today())
        
        if not results:
            st.warning("⚠️ Нет данных для экспорта. Сначала запустите анализ.")
            return
        
        # Экспорт в упрощённом формате с передачей БД для истории цен
        with st.spinner("📄 Создание Excel отчета..."):
            exporter = ExcelExporter()
            export_path = exporter.export_simple(results, date.today(), database=db)
            
            st.success(f"✅ Отчет создан: {export_path}")
            
            # Предложение скачать
            with open(export_path, 'rb') as f:
                st.download_button(
                    label="📥 Скачать Excel отчет",
                    data=f.read(),
                    file_name=export_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
    except Exception as e:
        st.error(f"❌ Ошибка при экспорте: {e}")
    finally:
        if db is not None:
            db.close()
