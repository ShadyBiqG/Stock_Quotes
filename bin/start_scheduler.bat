@echo off
chcp 65001 >nul
cls

REM Переход в корневую директорию проекта
cd /d "%~dp0\.."

echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║         📊 Stock Quotes Analyzer - Планировщик 📊           ║
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

REM Проверка зависимостей
echo 🔍 Проверка зависимостей...
python -c "import apscheduler" >nul 2>&1
if errorlevel 1 (
    echo ❌ APScheduler не установлен
    echo Запустите setup.bat для установки зависимостей
    pause
    exit /b 1
)
echo ✅ Зависимости в порядке
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

if not exist "Stock quotes.xlsx" (
    echo ⚠️  Stock quotes.xlsx не найден!
    echo Планировщик будет искать файл при каждом запуске
    echo.
)

REM Создание необходимых папок
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "output\exports" mkdir output\exports
if not exist "data\cache" mkdir data\cache

REM Проверка настроек планировщика
findstr /C:"enabled: true" config.yaml >nul
if errorlevel 1 (
    echo ⚠️  Планировщик отключен в config.yaml!
    echo.
    echo Откройте config.yaml и измените:
    echo   scheduler:
    echo     enabled: true
    echo.
    set /p CONTINUE="Продолжить все равно? (y/n): "
    if /i not "%CONTINUE%"=="y" exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                  ⏰ Запуск планировщика...                  ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 📅 Планировщик будет запускать анализ по расписанию из config.yaml
echo 📝 Логи сохраняются в logs\scheduler.log
echo.
echo ⚠️  Для остановки нажмите Ctrl+C
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

REM Запуск планировщика
python scheduler.py

pause
