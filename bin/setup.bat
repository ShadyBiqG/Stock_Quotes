@echo off
chcp 65001 >nul
cls

REM Переход в корневую директорию проекта
cd /d "%~dp0\.."

echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║          📊 Stock Quotes Analyzer - Установка 📊            ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo [1/5] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден!
    echo.
    echo Установите Python 3.10 или новее с https://www.python.org/
    echo Не забудьте отметить "Add Python to PATH" при установке!
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% найден
echo.

echo [2/5] Проверка виртуального окружения...
if exist "venv\" (
    echo ✅ Виртуальное окружение уже существует
) else (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Ошибка создания виртуального окружения
        pause
        exit /b 1
    )
    echo ✅ Виртуальное окружение создано
)
echo.

echo [3/5] Активация виртуального окружения...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Ошибка активации виртуального окружения
    pause
    exit /b 1
)
echo ✅ Виртуальное окружение активировано
echo.

echo [4/5] Проверка зависимостей...
echo 📦 Установка/обновление пакетов (это может занять 2-3 минуты)...
echo.

pip install --upgrade pip >nul 2>&1

pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ❌ Ошибка установки зависимостей
    echo Попробуйте запустить вручную: pip install -r requirements.txt
    pause
    exit /b 1
)
echo.
echo ✅ Все зависимости установлены
echo.

echo [5/5] Проверка конфигурации и структуры проекта...

REM Проверка структуры папок
if not exist "src\" mkdir src
if not exist "src\dashboards\" mkdir src\dashboards
if not exist "data\" mkdir data
if not exist "data\cache\" mkdir data\cache
if not exist "output\" mkdir output
if not exist "output\exports\" mkdir output\exports
if not exist "logs\" mkdir logs
if not exist "config\" mkdir config
echo ✅ Структура папок создана

REM Проверка файлов конфигурации
if not exist "config\api_keys.yaml" (
    echo ❌ Файл config\api_keys.yaml не найден!
    echo Создайте файл из примера: copy config\api_keys.example.yaml config\api_keys.yaml
    pause
    exit /b 1
)

if not exist "config\llm_config.yaml" (
    echo ❌ Файл config\llm_config.yaml не найден!
    echo Создайте файл из примера: copy config\llm_config.example.yaml config\llm_config.yaml
    pause
    exit /b 1
)

REM Проверка критических модулей
if not exist "src\data_loader.py" (
    echo ❌ Модуль src\data_loader.py не найден!
    pause
    exit /b 1
)
if not exist "src\llm_manager.py" (
    echo ❌ Модуль src\llm_manager.py не найден!
    pause
    exit /b 1
)
if not exist "src\company_info.py" (
    echo ❌ Модуль src\company_info.py не найден!
    pause
    exit /b 1
)
if not exist "src\database.py" (
    echo ❌ Модуль src\database.py не найден!
    pause
    exit /b 1
)
if not exist "src\analyzer.py" (
    echo ❌ Модуль src\analyzer.py не найден!
    pause
    exit /b 1
)
if not exist "src\excel_exporter.py" (
    echo ❌ Модуль src\excel_exporter.py не найден!
    pause
    exit /b 1
)
if not exist "main.py" (
    echo ❌ Файл main.py не найден!
    pause
    exit /b 1
)
if not exist "app.py" (
    echo ❌ Файл app.py не найден!
    pause
    exit /b 1
)
if not exist "src\dashboards\overview.py" (
    echo ❌ Дашборд src\dashboards\overview.py не найден!
    pause
    exit /b 1
)
if not exist "src\dashboards\settings.py" (
    echo ❌ Дашборд src\dashboards\settings.py не найден!
    pause
    exit /b 1
)
echo ✅ Все критические модули найдены

REM Проверка API ключа
findstr /C:"your-openrouter-api-key-here" config\api_keys.yaml >nul
if not errorlevel 1 (
    echo.
    echo ⚠️  ВНИМАНИЕ: API ключ не настроен!
    echo.
    echo Откройте config\api_keys.yaml и замените:
    echo   openrouter_api_key: "your-openrouter-api-key-here"
    echo на ваш ключ с https://openrouter.ai/
    echo.
    echo Или установите переменную окружения:
    echo   set OPENROUTER_API_KEY=ваш-ключ
    echo.
) else (
    echo ✅ API ключ настроен
)
echo.

if not exist "Stock quotes.xlsx" (
    echo ⚠️  Предупреждение: Stock quotes.xlsx не найден
    echo Создайте файл Excel с колонками: Ticker, Price, Change, Volume
    echo Или скопируйте тестовый файл из репозитория
    echo.
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║                    ✅ Установка завершена! ✅                ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                  📝 ВАЖНАЯ ИНФОРМАЦИЯ 📝                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 🔑 Настройка API ключа:
echo    1. Зарегистрируйтесь на https://openrouter.ai/
echo    2. Получите API ключ
echo    3. Откройте config\api_keys.yaml и добавьте ваш API ключ
echo    4. Замените openrouter_api_key на ваш ключ
echo    5. Пополните баланс ($10-20 для начала)
echo.
echo 📊 Добавление компаний:
echo    - В веб-интерфейсе: Настройки → Управление компаниями
echo    - Достаточно указать только Ticker
echo    - Остальная информация получится автоматически через LLM
echo.
echo 🚀 Запуск приложения:
echo.
echo   🌐 Веб-интерфейс (рекомендуется):  start_web.bat
echo   📊 CLI версия:                      start.bat
echo   ⏰ Планировщик:                     start_scheduler.bat
echo.
echo 💡 Совет: Начните с веб-интерфейса - там все настройки в визуальном виде!
echo.
pause
