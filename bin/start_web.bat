@echo off
chcp 65001 >nul
cls

REM Переход в корневую директорию проекта
cd /d "%~dp0\.."

echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║       📊 Stock Quotes Analyzer - Веб-интерфейс 📊           ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден!
    echo Запустите setup.bat для первоначальной настройки
    pause
    exit /b 1
)

REM Проверка виртуального окружения
if not exist "venv\" (
    echo ⚠️  Виртуальное окружение не найдено
    echo Запустите setup.bat для первоначальной настройки
    pause
    exit /b 1
)

REM Активация виртуального окружения
echo 🔧 Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Проверка критических зависимостей
echo 🔍 Проверка зависимостей...

python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo ❌ Streamlit не установлен
    echo Запустите setup.bat для установки зависимостей
    pause
    exit /b 1
)

python -c "import pandas" 2>nul
if errorlevel 1 (
    echo ❌ Pandas не установлен
    echo Запустите setup.bat для установки зависимостей
    pause
    exit /b 1
)

python -c "import plotly" 2>nul
if errorlevel 1 (
    echo ❌ Plotly не установлен
    echo Запустите setup.bat для установки зависимостей
    pause
    exit /b 1
)

python -c "import openai" 2>nul
if errorlevel 1 (
    echo ❌ OpenAI SDK не установлен
    echo Запустите setup.bat для установки зависимостей
    pause
    exit /b 1
)

python -c "import nest_asyncio" 2>nul
if errorlevel 1 (
    echo ❌ nest_asyncio не установлен
    echo Запустите setup.bat для установки зависимостей
    pause
    exit /b 1
)

echo ✅ Все зависимости установлены
echo.

REM Проверка файлов конфигурации
if not exist "config\api_keys.yaml" (
    echo ❌ config\api_keys.yaml не найден!
    echo Создайте файл из примера: copy config\api_keys.example.yaml config\api_keys.yaml
    pause
    exit /b 1
)

if not exist "config\llm_config.yaml" (
    echo ❌ config\llm_config.yaml не найден!
    echo Создайте файл из примера: copy config\llm_config.example.yaml config\llm_config.yaml
    pause
    exit /b 1
)

REM Проверка API ключа (предупреждение, но не блокировка)
findstr /C:"your-openrouter-api-key-here" config\api_keys.yaml >nul
if not errorlevel 1 (
    echo.
    echo ⚠️  ВНИМАНИЕ: API ключ не настроен!
    echo    Настройте ключ в config\api_keys.yaml для работы анализа
    echo    https://openrouter.ai/
    echo.
)

REM Создание необходимых папок
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "output\exports" mkdir output\exports
if not exist "data\cache" mkdir data\cache

REM Получение IP адреса
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do set LOCAL_IP=%%a
set LOCAL_IP=%LOCAL_IP: =%

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                  🌐 Запуск веб-приложения...                ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 📍 Приложение будет доступно по адресам:
echo.
echo    💻 Локально:        http://localhost:8501
echo    📱 В сети Wi-Fi:    http://%LOCAL_IP%:8501
echo.
echo 💡 Откройте один из адресов в браузере
echo 📱 Второй адрес можно использовать на телефоне в той же Wi-Fi сети
echo.
echo ⚠️  Для остановки нажмите Ctrl+C
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

REM Запуск Streamlit
streamlit run app.py

pause
