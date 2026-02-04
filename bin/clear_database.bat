@echo off
chcp 65001 > nul
title Очистка базы данных Stock Quotes

REM Переход в корневую директорию проекта
cd /d "%~dp0\.."

echo.
echo ═══════════════════════════════════════════════════════════════
echo   🗑️  ОЧИСТКА БАЗЫ ДАННЫХ STOCK QUOTES
echo ═══════════════════════════════════════════════════════════════
echo.

REM Проверка наличия Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден!
    echo    Установите Python с python.org
    echo.
    pause
    exit /b 1
)

REM Показать информацию о БД
echo 📊 Текущее состояние базы данных:
echo.
python scripts\clear_database.py --info

echo.
echo.
echo ═══════════════════════════════════════════════════════════════
echo   ВЫБЕРИТЕ ДЕЙСТВИЕ:
echo ═══════════════════════════════════════════════════════════════
echo.
echo   1. Очистить все таблицы (рекомендуется)
echo      • Удаляет все записи
echo      • Сохраняет структуру БД
echo      • Быстрее при следующем запуске
echo.
echo   2. Удалить файл БД полностью
echo      • Полностью удаляет файл БД
echo      • БД будет пересоздана при запуске
echo.
echo   3. Показать информацию (без очистки)
echo.
echo   0. Выход
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

set /p choice="   Ваш выбор (0-3): "

if "%choice%"=="1" goto CLEAR_TABLES
if "%choice%"=="2" goto DELETE_FILE
if "%choice%"=="3" goto SHOW_INFO
if "%choice%"=="0" goto EXIT

echo.
echo ❌ Неверный выбор!
timeout /t 2 > nul
goto EXIT

:CLEAR_TABLES
echo.
echo ═══════════════════════════════════════════════════════════════
python scripts\clear_database.py --clear
goto END

:DELETE_FILE
echo.
echo ═══════════════════════════════════════════════════════════════
python scripts\clear_database.py --delete
goto END

:SHOW_INFO
echo.
echo ═══════════════════════════════════════════════════════════════
python scripts\clear_database.py --info
goto END

:END
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
pause
goto EXIT

:EXIT
