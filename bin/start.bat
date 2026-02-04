@echo off
chcp 65001 >nul
cls

REM Переход в корневую директорию проекта
cd /d "%~dp0\.."

echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║          📊 Stock Quotes Analyzer - CLI Запуск 📊           ║
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
python -c "import pandas, yaml, openai, yfinance, tqdm" >nul 2>&1
if errorlevel 1 (
    echo ❌ Не все зависимости установлены
    echo Запустите setup.bat для установки зависимостей
    pause
    exit /b 1
)
echo ✅ Зависимости в порядке
echo.

REM Проверка файлов
if not exist "config.yaml" (
    echo ❌ config.yaml не найден!
    pause
    exit /b 1
)

if not exist "Stock quotes.xlsx" (
    echo ❌ Stock quotes.xlsx не найден!
    echo Поместите файл с котировками в корень проекта
    pause
    exit /b 1
)

REM Проверка API ключа
findstr /C:"your-openrouter-api-key-here" config.yaml >nul
if not errorlevel 1 (
    echo ⚠️  API ключ не настроен в config.yaml!
    echo Откройте config.yaml и добавьте ваш ключ с https://openrouter.ai/
    echo.
    echo Или установите переменную окружения:
    set /p API_KEY="Введите API ключ (или Enter для выхода): "
    if "%API_KEY%"=="" (
        pause
        exit /b 1
    )
    set OPENROUTER_API_KEY=%API_KEY%
)

REM Создание необходимых папок
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "output\exports" mkdir output\exports
if not exist "data\cache" mkdir data\cache

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🚀 Запуск анализа...                     ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Запуск основного скрипта
python main.py

REM Проверка результата
if errorlevel 1 (
    echo.
    echo ❌ Анализ завершился с ошибкой
    echo Проверьте логи в logs\analysis.log
) else (
    echo.
    echo ╔══════════════════════════════════════════════════════════════╗
    echo ║                    ✅ Анализ завершен! ✅                    ║
    echo ╚══════════════════════════════════════════════════════════════╝
    echo.
    echo 📄 Excel отчет создан в output\exports\
    echo 💾 Данные сохранены в data\stock_analysis.db
    echo 📝 Логи доступны в logs\analysis.log
)

echo.
pause
