"""
Дашборд "Точность" - анализ точности прогнозов моделей
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database


def show(config: dict):
    """
    Отображение дашборда "Точность"
    
    Args:
        config: Конфигурация приложения
    """
    st.title("🎯 Анализ точности моделей")
    st.markdown("Сравнение эффективности различных LLM моделей")
    
    # Подключение к БД
    try:
        db = Database(config['database']['path'])
    except Exception as e:
        st.error(f"Ошибка подключения к БД: {e}")
        return
    
    st.info("""
    ℹ️ **Примечание:** Данный дашборд показывает статистику консенсуса и согласованности моделей.
    
    Для полного анализа точности необходимо сравнение прогнозов с реальными изменениями котировок на следующий день.
    Эта функциональность будет доступна после накопления достаточного объема исторических данных.
    """)
    
    # Фильтры
    col1, col2 = st.columns([3, 1])
    
    with col1:
        date_range = st.slider(
            "Период анализа (дней)",
            min_value=7,
            max_value=90,
            value=30
        )
    
    with col2:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()
    
    # Сбор данных за период
    start_date = date.today() - timedelta(days=date_range)
    
    all_results = []
    for day_offset in range(date_range + 1):
        check_date = date.today() - timedelta(days=day_offset)
        results = db.get_analysis_results(analysis_date=check_date)
        
        for r in results:
            r['analysis_date'] = check_date
            all_results.append(r)
    
    if not all_results:
        st.warning("⚠️ Недостаточно данных для анализа")
        st.info("💡 Выполните несколько анализов за разные дни")
        return
    
    df = pd.DataFrame(all_results)
    
    # Метрики
    st.markdown("### 📊 Общая статистика")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        unique_analyses = df['analysis_date'].nunique()
        st.metric("Дней анализа", unique_analyses)
    
    with col2:
        total_predictions = len(df)
        st.metric("Всего прогнозов", total_predictions)
    
    with col3:
        models_count = df['model_name'].nunique()
        st.metric("Моделей", models_count)
    
    with col4:
        avg_tokens = int(df['tokens_used'].mean())
        st.metric("Ср. токенов", f"{avg_tokens}")
    
    # Статистика по моделям
    st.markdown("### 🤖 Статистика по моделям")
    
    models_stats = []
    
    for model in df['model_name'].unique():
        model_data = df[df['model_name'] == model]
        
        # Распределение прогнозов
        predictions = model_data['prediction'].value_counts()
        
        # Уверенность
        confidence_dist = model_data['confidence'].value_counts()
        
        # Токены
        avg_tokens = model_data['tokens_used'].mean()
        
        models_stats.append({
            'Модель': model,
            'Прогнозов': len(model_data),
            'РАСТЕТ': predictions.get('РАСТЕТ', 0),
            'ПАДАЕТ': predictions.get('ПАДАЕТ', 0),
            'СТАБИЛЬНА': predictions.get('СТАБИЛЬНА', 0),
            'Высокая уверенность': confidence_dist.get('ВЫСОКАЯ', 0),
            'Средняя уверенность': confidence_dist.get('СРЕДНЯЯ', 0),
            'Низкая уверенность': confidence_dist.get('НИЗКАЯ', 0),
            'Ср. токенов': int(avg_tokens)
        })
    
    df_models = pd.DataFrame(models_stats)
    
    st.dataframe(df_models, use_container_width=True)
    
    # Графики распределения
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Распределение прогнозов")
        
        # Подготовка данных
        chart_data = []
        for model in df['model_name'].unique():
            model_data = df[df['model_name'] == model]
            predictions = model_data['prediction'].value_counts()
            
            for pred, count in predictions.items():
                chart_data.append({
                    'Модель': model,
                    'Прогноз': pred,
                    'Количество': count
                })
        
        df_chart = pd.DataFrame(chart_data)
        
        fig = px.bar(
            df_chart,
            x='Модель',
            y='Количество',
            color='Прогноз',
            barmode='group',
            color_discrete_map={
                'РАСТЕТ': '#90EE90',
                'ПАДАЕТ': '#FFB6C1',
                'СТАБИЛЬНА': '#FFD700'
            }
        )
        
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Уверенность моделей")
        
        # Подготовка данных
        conf_data = []
        for model in df['model_name'].unique():
            model_data = df[df['model_name'] == model]
            confidence = model_data['confidence'].value_counts()
            
            for conf, count in confidence.items():
                conf_data.append({
                    'Модель': model,
                    'Уверенность': conf,
                    'Количество': count
                })
        
        df_conf = pd.DataFrame(conf_data)
        
        fig = px.bar(
            df_conf,
            x='Модель',
            y='Количество',
            color='Уверенность',
            barmode='stack',
            color_discrete_map={
                'ВЫСОКАЯ': '#90EE90',
                'СРЕДНЯЯ': '#FFD700',
                'НИЗКАЯ': '#FFB6C1'
            }
        )
        
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Консенсус анализ
    st.markdown("### 🤝 Анализ консенсуса")
    
    # Группировка по акциям и датам
    grouped = df.groupby(['ticker', 'analysis_date'])['prediction'].apply(list).reset_index()
    
    # Вычисление консенсуса
    def calc_consensus(predictions):
        if len(set(predictions)) == 1:
            return 'Полный'
        elif len(set(predictions)) == 2:
            from collections import Counter
            counts = Counter(predictions)
            most_common = counts.most_common(1)[0]
            if most_common[1] > len(predictions) / 2:
                return 'Частичный'
        return 'Нет'
    
    grouped['consensus'] = grouped['prediction'].apply(calc_consensus)
    
    consensus_counts = grouped['consensus'].value_counts()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### Статистика консенсуса")
        
        total = len(grouped)
        
        if 'Полный' in consensus_counts:
            full = consensus_counts['Полный']
            st.metric("Полный консенсус", f"{full} ({full/total*100:.1f}%)")
        
        if 'Частичный' in consensus_counts:
            partial = consensus_counts['Частичный']
            st.metric("Частичный консенсус", f"{partial} ({partial/total*100:.1f}%)")
        
        if 'Нет' in consensus_counts:
            none = consensus_counts['Нет']
            st.metric("Без консенсуса", f"{none} ({none/total*100:.1f}%)")
    
    with col2:
        # Pie chart
        fig = px.pie(
            values=consensus_counts.values,
            names=consensus_counts.index,
            color=consensus_counts.index,
            color_discrete_map={
                'Полный': '#90EE90',
                'Частичный': '#FFD700',
                'Нет': '#FFB6C1'
            },
            hole=0.4
        )
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Использование токенов
    st.markdown("### 💰 Использование токенов")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # По моделям
        tokens_by_model = df.groupby('model_name')['tokens_used'].sum().reset_index()
        tokens_by_model.columns = ['Модель', 'Всего токенов']
        
        fig = px.bar(
            tokens_by_model,
            x='Модель',
            y='Всего токенов',
            color='Модель'
        )
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        total_tokens = tokens_by_model['Всего токенов'].sum()
        st.info(f"💡 Всего использовано токенов: **{total_tokens:,}**")
    
    with col2:
        # По дням
        tokens_by_date = df.groupby('analysis_date')['tokens_used'].sum().reset_index()
        tokens_by_date.columns = ['Дата', 'Токенов']
        tokens_by_date = tokens_by_date.sort_values('Дата')
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=tokens_by_date['Дата'],
            y=tokens_by_date['Токенов'],
            mode='lines+markers',
            fill='tonexty',
            name='Токены'
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Дата",
            yaxis_title="Токенов"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        avg_tokens_day = total_tokens / max(unique_analyses, 1)
        st.info(f"💡 Среднее использование в день: **{avg_tokens_day:,.0f}** токенов")
    
    db.close()
