@echo off
chcp 65001 >nul
cls

echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║          📦 Проверка зависимостей и окружения 📦            ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Проверка Python
echo [1] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не установлен
    echo    Скачайте с https://www.python.org/
    set PYTHON_OK=0
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo ✅ Python %PYTHON_VERSION%
    set PYTHON_OK=1
)
echo.

REM Проверка pip
echo [2] Проверка pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip не найден
    set PIP_OK=0
) else (
    for /f "tokens=2" %%i in ('pip --version 2^>^&1') do set PIP_VERSION=%%i
    echo ✅ pip %PIP_VERSION%
    set PIP_OK=1
)
echo.

REM Проверка виртуального окружения
echo [3] Проверка виртуального окружения...
if exist "venv\" (
    echo ✅ Виртуальное окружение найдено (venv\)
    set VENV_OK=1
) else (
    echo ⚠️  Виртуальное окружение не создано
    echo    Запустите setup.bat для создания
    set VENV_OK=0
)
echo.

REM Активация venv для проверки пакетов
if exist "venv\" (
    call venv\Scripts\activate.bat
)

REM Проверка основных пакетов
echo [4] Проверка установленных пакетов...
echo.

set MISSING_COUNT=0

python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo ❌ pandas - не установлен
    set /a MISSING_COUNT+=1
) else (
    for /f "tokens=2" %%i in ('pip show pandas 2^>^&1 ^| findstr "Version:"') do echo ✅ pandas %%i
)

python -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo ❌ openpyxl - не установлен
    set /a MISSING_COUNT+=1
) else (
    for /f "tokens=2" %%i in ('pip show openpyxl 2^>^&1 ^| findstr "Version:"') do echo ✅ openpyxl %%i
)

python -c "import yaml" >nul 2>&1
if errorlevel 1 (
    echo ❌ pyyaml - не установлен
    set /a MISSING_COUNT+=1
) else (
    for /f "tokens=2" %%i in ('pip show pyyaml 2^>^&1 ^| findstr "Version:"') do echo ✅ pyyaml %%i
)

python -c "import openai" >nul 2>&1
if errorlevel 1 (
    echo ❌ openai - не установлен
    set /a MISSING_COUNT+=1
) else (
    for /f "tokens=2" %%i in ('pip show openai 2^>^&1 ^| findstr "Version:"') do echo ✅ openai %%i
)

python -c "import yfinance" >nul 2>&1
if errorlevel 1 (
    echo ❌ yfinance - не установлен
    set /a MISSING_COUNT+=1
) else (
    for /f "tokens=2" %%i in ('pip show yfinance 2^>^&1 ^| findstr "Version:"') do echo ✅ yfinance %%i
)

python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo ❌ streamlit - не установлен
    set /a MISSING_COUNT+=1
) else (
    for /f "tokens=2" %%i in ('pip show streamlit 2^>^&1 ^| findstr "Version:"') do echo ✅ streamlit %%i
)

python -c "import plotly" >nul 2>&1
if errorlevel 1 (
    echo ❌ plotly - не установлен
    set /a MISSING_COUNT+=1
) else (
    for /f "tokens=2" %%i in ('pip show plotly 2^>^&1 ^| findstr "Version:"') do echo ✅ plotly %%i
)

python -c "import apscheduler" >nul 2>&1
if errorlevel 1 (
    echo ❌ apscheduler - не установлен
    set /a MISSING_COUNT+=1
) else (
    for /f "tokens=2" %%i in ('pip show apscheduler 2^>^&1 ^| findstr "Version:"') do echo ✅ apscheduler %%i
)

python -c "import tqdm" >nul 2>&1
if errorlevel 1 (
    echo ❌ tqdm - не установлен
    set /a MISSING_COUNT+=1
) else (
    for /f "tokens=2" %%i in ('pip show tqdm 2^>^&1 ^| findstr "Version:"') do echo ✅ tqdm %%i
)

echo.

REM Проверка файлов проекта
echo [5] Проверка файлов проекта...
echo.

if exist "config.yaml" (
    echo ✅ config.yaml найден
) else (
    echo ❌ config.yaml не найден
)

if exist "Stock quotes.xlsx" (
    echo ✅ Stock quotes.xlsx найден
) else (
    echo ⚠️  Stock quotes.xlsx не найден
)

if exist "main.py" (
    echo ✅ main.py найден
) else (
    echo ❌ main.py не найден
)

if exist "app.py" (
    echo ✅ app.py найден
) else (
    echo ❌ app.py не найден
)

if exist "requirements.txt" (
    echo ✅ requirements.txt найден
) else (
    echo ❌ requirements.txt не найден
)

echo.

REM Проверка API ключа
echo [6] Проверка конфигурации...
if exist "config.yaml" (
    findstr /C:"your-openrouter-api-key-here" config.yaml >nul
    if not errorlevel 1 (
        echo ⚠️  API ключ не настроен в config.yaml
        echo    Откройте config.yaml и добавьте ваш ключ
    ) else (
        echo ✅ API ключ настроен в config.yaml
    )
) else (
    echo ❌ config.yaml не найден
)

echo.

REM Итоговый отчет
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                      📊 ИТОГОВЫЙ ОТЧЕТ                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

if %PYTHON_OK%==1 if %PIP_OK%==1 if %VENV_OK%==1 if %MISSING_COUNT%==0 (
    echo ✅ Все проверки пройдены успешно!
    echo.
    echo 🚀 Вы можете запустить приложение:
    echo    • CLI версия:         start.bat
    echo    • Веб-интерфейс:      start_web.bat
    echo    • Планировщик:        start_scheduler.bat
) else (
    echo ⚠️  Обнаружены проблемы:
    echo.
    if %PYTHON_OK%==0 echo    • Python не установлен
    if %PIP_OK%==0 echo    • pip не установлен
    if %VENV_OK%==0 echo    • Виртуальное окружение не создано
    if %MISSING_COUNT% GTR 0 echo    • Не хватает %MISSING_COUNT% пакетов
    echo.
    echo 🔧 Запустите setup.bat для автоматической установки
)

echo.
pause
