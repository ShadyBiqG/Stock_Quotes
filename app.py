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
    """Загрузка конфигурации (v3.0: поддержка новой структуры)"""
    import logging
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    
    try:
        # v3.0: Проверка новой структуры config/
        config_dir = Path("config")
        api_keys_path = config_dir / "api_keys.yaml"
        llm_config_path = config_dir / "llm_config.yaml"
        companies_path = config_dir / "companies.json"
        
        # Если есть новая структура - используем её
        if api_keys_path.exists() and llm_config_path.exists():
            config = {}
            
            # API ключи
            with open(api_keys_path, 'r', encoding='utf-8') as f:
                api_keys = yaml.safe_load(f)
                config['openrouter'] = {
                    'api_key': api_keys.get('openrouter_api_key', ''),
                    'base_url': 'https://openrouter.ai/api/v1'
                }
                # Сохраняем alphavantage_api_key отдельно
                saved_alphavantage_key = api_keys.get('alphavantage_api_key', '')
            
            # LLM конфигурация
            with open(llm_config_path, 'r', encoding='utf-8') as f:
                llm_config = yaml.safe_load(f)
                # Сохраняем api_key перед обновлением
                saved_api_key = config['openrouter']['api_key']
                saved_base_url = config['openrouter']['base_url']
                
                config.update(llm_config)
                
                # Восстанавливаем api_key и обновляем base_url
                if 'openrouter' not in config:
                    config['openrouter'] = {}
                config['openrouter']['api_key'] = saved_api_key
                if 'openrouter' in llm_config and 'base_url' in llm_config['openrouter']:
                    config['openrouter']['base_url'] = llm_config['openrouter']['base_url']
                else:
                    config['openrouter']['base_url'] = saved_base_url
                
                # Добавляем alphavantage_api_key в company_info
                if 'company_info' not in config:
                    config['company_info'] = {}
                config['company_info']['alphavantage_api_key'] = saved_alphavantage_key
            
            # Путь к списку компаний
            if companies_path.exists():
                config['input'] = {'excel_file': str(companies_path)}
            else:
                st.warning(f"Файл {companies_path} не найден")
                config['input'] = {'excel_file': ''}
            
            return config
        
        # Fallback на старый config.yaml
        config_path = Path("config.yaml")
        if config_path.exists():
            st.warning("⚠️ Используется старый формат config.yaml. Рекомендуется миграция на v3.0")
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        
        st.error("Конфигурация не найдена! Создайте config/api_keys.yaml и config/llm_config.yaml")
        return None
        
    except Exception as e:
        st.error(f"Ошибка загрузки конфигурации: {e}")
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
