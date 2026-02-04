"""
Дашборд "История" - исторические тренды и прогнозы
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database


def show(config: dict):
    """
    Отображение дашборда "История"
    
    Args:
        config: Конфигурация приложения
    """
    st.title("📜 История трендов")
    st.markdown("Исторические данные по котировкам и прогнозам")
    
    # Подключение к БД
    try:
        db = Database(config['database']['path'])
    except Exception as e:
        st.error(f"Ошибка подключения к БД: {e}")
        return
    
    # Фильтры
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Получение доступных тикеров
        results = db.get_analysis_results(analysis_date=date.today())
        
        if not results:
            # Попробовать предыдущие дни
            for days_back in range(1, 8):
                check_date = date.today() - timedelta(days=days_back)
                results = db.get_analysis_results(analysis_date=check_date)
                if results:
                    break
        
        if not results:
            st.warning("⚠️ Нет исторических данных")
            st.info("💡 Выполните несколько анализов, чтобы увидеть историю")
            return
        
        tickers = sorted(list(set(r['ticker'] for r in results)))
        selected_ticker = st.selectbox("Выберите акцию", tickers)
    
    with col2:
        days_history = st.number_input(
            "Дней истории",
            min_value=7,
            max_value=365,
            value=30
        )
    
    with col3:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()
    
    # Получение исторических данных
    history_data = db.get_historical_data(selected_ticker, days=days_history)
    
    if not history_data:
        st.warning(f"⚠️ Нет исторических данных по {selected_ticker}")
        return
    
    # Преобразование в DataFrame
    df = pd.DataFrame(history_data)
    df['date'] = pd.to_datetime(df['date'])
    
    # Группировка по датам
    dates = df['date'].unique()
    
    st.markdown(f"### 📊 История: {selected_ticker}")
    st.markdown(f"Период: {len(dates)} дней анализа")
    
    # График цены и изменений
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💰 Цена")
        
        # Подготовка данных
        price_data = df.groupby('date')['price'].first().reset_index()
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=price_data['date'],
            y=price_data['price'],
            mode='lines+markers',
            name='Цена',
            line=dict(color='#4472C4', width=2),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Дата",
            yaxis_title="Цена (USD)",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📈 Изменение (%)")
        
        # Подготовка данных
        change_data = df.groupby('date')['change'].first().reset_index()
        
        # Цвет в зависимости от знака
        colors = ['#90EE90' if c > 0 else '#FFB6C1' for c in change_data['change']]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=change_data['date'],
            y=change_data['change'],
            name='Изменение',
            marker_color=colors
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Дата",
            yaxis_title="Изменение (%)",
            hovermode='x'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Прогнозы моделей во времени
    st.markdown("#### 🤖 Прогнозы моделей")
    
    # Подготовка данных
    models = df['model_name'].unique()
    
    if len(models) > 0:
        # Pivot для каждой модели
        fig = go.Figure()
        
        prediction_map = {'РАСТЕТ': 1, 'СТАБИЛЬНА': 0, 'ПАДАЕТ': -1}
        
        for model in models:
            model_data = df[df['model_name'] == model].copy()
            model_data = model_data.groupby('date')['prediction'].first().reset_index()
            
            # Преобразование прогнозов в числа
            model_data['prediction_num'] = model_data['prediction'].map(prediction_map)
            
            fig.add_trace(go.Scatter(
                x=model_data['date'],
                y=model_data['prediction_num'],
                mode='lines+markers',
                name=model,
                line=dict(width=2),
                marker=dict(size=8)
            ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Дата",
            yaxis_title="Прогноз",
            yaxis=dict(
                tickmode='array',
                tickvals=[-1, 0, 1],
                ticktext=['ПАДАЕТ', 'СТАБИЛЬНА', 'РАСТЕТ']
            ),
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Уверенность моделей
    st.markdown("#### 💪 Уверенность моделей")
    
    confidence_data = df.groupby(['date', 'model_name'])['confidence'].first().reset_index()
    
    confidence_map = {'ВЫСОКАЯ': 3, 'СРЕДНЯЯ': 2, 'НИЗКАЯ': 1}
    confidence_data['confidence_num'] = confidence_data['confidence'].map(confidence_map)
    
    fig = px.line(
        confidence_data,
        x='date',
        y='confidence_num',
        color='model_name',
        markers=True
    )
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Дата",
        yaxis_title="Уверенность",
        yaxis=dict(
            tickmode='array',
            tickvals=[1, 2, 3],
            ticktext=['НИЗКАЯ', 'СРЕДНЯЯ', 'ВЫСОКАЯ']
        ),
        legend_title="Модель"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Таблица истории
    st.markdown("#### 📋 Таблица истории")
    
    # Подготовка таблицы
    table_data = []
    
    for d in dates:
        date_data = df[df['date'] == d]
        
        row = {
            'Дата': d.strftime('%Y-%m-%d'),
            'Цена': f"${date_data['price'].iloc[0]:.2f}",
            'Изм.%': f"{date_data['change'].iloc[0]:+.2f}%"
        }
        
        # Прогнозы моделей
        for model_name in models:
            model_row = date_data[date_data['model_name'] == model_name]
            if not model_row.empty:
                prediction = model_row['prediction'].iloc[0]
                confidence = model_row['confidence'].iloc[0]
                row[model_name] = f"{prediction} ({confidence})"
            else:
                row[model_name] = '-'
        
        table_data.append(row)
    
    df_table = pd.DataFrame(table_data)
    df_table = df_table.sort_values('Дата', ascending=False)
    
    st.dataframe(df_table, use_container_width=True, height=300)
    
    # Экспорт
    if st.button("📥 Скачать историю (CSV)"):
        csv = df_table.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="💾 Сохранить CSV",
            data=csv,
            file_name=f"{selected_ticker}_history.csv",
            mime="text/csv"
        )
    
    db.close()
