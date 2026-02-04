"""
Веб-приложение Streamlit для анализа котировок акций
Адаптивный интерфейс для телефона и компьютера
"""

import streamlit as st
import yaml
import sys
from pathlib import Path

# Добавление src в путь
sys.path.insert(0, str(Path(__file__).parent))

# Конфигурация страницы
st.set_page_config(
    page_title="Stock Quotes Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Загрузка конфигурации
@st.cache_resource
def load_config():
    """Загрузка конфигурации"""
    try:
        with open("config.yaml", 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        st.error(f"Ошибка загрузки config.yaml: {e}")
        return None

config = load_config()

# CSS для адаптивного дизайна
st.markdown("""
<style>
    /* Адаптивный дизайн */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem !important;
        }
        
        h1 {
            font-size: 1.5rem !important;
        }
        
        h2 {
            font-size: 1.2rem !important;
        }
    }
    
    /* Улучшение карточек метрик */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    
    /* Таблицы */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Темная тема кнопок */
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Сайдбар - навигация
st.sidebar.title("📊 Stock Analyzer")
st.sidebar.markdown("---")

# Навигация
page = st.sidebar.radio(
    "Навигация",
    [
        "🏠 Обзор",
        "📈 Анализ",
        "📜 История",
        "🎯 Точность",
        "⚙️ Настройки"
    ]
)

st.sidebar.markdown("---")

# Информация о приложении
with st.sidebar.expander("ℹ️ О приложении"):
    st.markdown("""
    **Stock Quotes Analyzer**
    
    Анализ котировок акций через OpenRouter API с использованием множественных LLM моделей.
    
    **Возможности:**
    - 🤖 Анализ через 3+ LLM
    - 📊 Интерактивные дашборды
    - 📱 Адаптивный дизайн
    - 🔄 Автоматизация
    """)

# Импорт дашбордов
from src.dashboards import overview, analysis, history, accuracy, settings

# Маршрутизация страниц
if page == "🏠 Обзор":
    overview.show(config)
elif page == "📈 Анализ":
    analysis.show(config)
elif page == "📜 История":
    history.show(config)
elif page == "🎯 Точность":
    accuracy.show(config)
elif page == "⚙️ Настройки":
    settings.show(config)

# Футер
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.8rem;'>
        Made with ❤️ using Streamlit<br>
        Stock Quotes Analyzer v1.0
    </div>
    """,
    unsafe_allow_html=True
)
