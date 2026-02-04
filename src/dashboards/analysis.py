"""
Дашборд "Анализ" - детальный просмотр результатов анализа
"""

import streamlit as st
import pandas as pd
from datetime import date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database


def show(config: dict):
    """
    Отображение дашборда "Анализ"
    
    Args:
        config: Конфигурация приложения
    """
    st.title("📈 Детальный анализ")
    st.markdown("Просмотр результатов анализа с причинами и описаниями компаний")
    
    # Подключение к БД
    try:
        db = Database(config['database']['path'])
    except Exception as e:
        st.error(f"Ошибка подключения к БД: {e}")
        return
    
    # Фильтры
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        selected_date = st.date_input(
            "Дата анализа",
            value=date.today(),
            max_value=date.today()
        )
    
    with col2:
        # Получение списка тикеров
        results = db.get_analysis_results(analysis_date=selected_date)
        
        if not results:
            st.warning("⚠️ Нет данных за выбранную дату")
            return
        
        tickers = sorted(list(set(r['ticker'] for r in results)))
        selected_ticker = st.selectbox("Выберите акцию", ["Все"] + tickers)
    
    with col3:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()
    
    # Фильтрация по тикеру
    if selected_ticker != "Все":
        results = [r for r in results if r['ticker'] == selected_ticker]
    
    # Группировка по тикерам
    stocks_data = {}
    for r in results:
        ticker = r['ticker']
        if ticker not in stocks_data:
            stocks_data[ticker] = {
                'ticker': ticker,
                'name': r.get('name', ''),
                'description': r.get('description', ''),
                'sector': r.get('sector', ''),
                'price': r['price'],
                'change': r['change'],
                'volume': r['volume'],
                'models': []
            }
        
        stocks_data[ticker]['models'].append({
            'model_name': r['model_name'],
            'prediction': r['prediction'],
            'reasons': r['reasons'],
            'confidence': r['confidence'],
            'validation': r.get('validation_flags', {}),
            'tokens': r.get('tokens_used', 0)
        })
    
    # Отображение акций
    for ticker, data in stocks_data.items():
        with st.expander(f"**{ticker}** - {data['name']}", expanded=(selected_ticker != "Все")):
            
            # Информация о компании
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"### {data['name']}")
                
                if data['description']:
                    st.markdown(f"**Описание:** {data['description']}")
                
                if data['sector']:
                    st.markdown(f"**Сектор:** {data['sector']}")
            
            with col2:
                # Метрики
                st.metric("Цена", f"${data['price']:.2f}")
                st.metric("Изменение", f"{data['change']:+.2f}%")
                st.metric("Объем", f"{data['volume']:,}")
            
            st.markdown("---")
            
            # Результаты моделей
            st.markdown("### 🤖 Прогнозы моделей")
            
            for model in data['models']:
                # Карточка модели
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"#### {model['model_name']}")
                
                with col2:
                    # Цветовое кодирование прогноза
                    prediction_color = {
                        'РАСТЕТ': '🟢',
                        'ПАДАЕТ': '🔴',
                        'СТАБИЛЬНА': '🟡',
                        'ОШИБКА': '⚫'
                    }.get(model['prediction'], '⚪')
                    
                    st.markdown(f"**Прогноз:** {prediction_color} {model['prediction']}")
                
                with col3:
                    # Уверенность
                    confidence_emoji = {
                        'ВЫСОКАЯ': '💪',
                        'СРЕДНЯЯ': '👍',
                        'НИЗКАЯ': '🤷'
                    }.get(model['confidence'], '❓')
                    
                    st.markdown(f"**Уверенность:** {confidence_emoji} {model['confidence']}")
                
                # Причины
                if model['reasons']:
                    st.markdown("**Причины:**")
                    for i, reason in enumerate(model['reasons'], 1):
                        st.markdown(f"{i}. {reason}")
                else:
                    st.warning("Причины не указаны")
                
                # Валидация
                validation = model.get('validation', {})
                if validation:
                    trust_level = validation.get('trust_level', 'UNKNOWN')
                    
                    if trust_level == 'LOW':
                        st.warning("⚠️ Низкий уровень доверия к ответу")
                        
                        suspicious = validation.get('suspicious_patterns', [])
                        if suspicious:
                            st.markdown(f"Подозрительные паттерны: {', '.join(suspicious)}")
                
                # Токены
                st.caption(f"Использовано токенов: {model['tokens']}")
                
                st.markdown("---")
            
            # Консенсус
            predictions = [m['prediction'] for m in data['models']]
            
            if len(set(predictions)) == 1:
                st.success(f"✅ Все модели согласны: **{predictions[0]}**")
            else:
                from collections import Counter
                counts = Counter(predictions)
                most_common = counts.most_common(1)[0]
                
                if most_common[1] > len(predictions) / 2:
                    st.info(
                        f"ℹ️ Большинство моделей ({most_common[1]}/{len(predictions)}) "
                        f"прогнозируют: **{most_common[0]}**"
                    )
                else:
                    st.warning(
                        f"⚠️ Модели не пришли к консенсусу. "
                        f"Разные мнения: {dict(counts)}"
                    )
    
    db.close()
