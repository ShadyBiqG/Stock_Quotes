@echo off
chcp 65001 >nul
cls

echo.
echo ============================================================
echo   ТЕСТ ЗАГРУЗКИ КОТИРОВОК
echo ============================================================
echo.

REM Проверка Python
where python >nul 2>&1
if errorlevel 1 (
    echo [X] Python не найден в PATH!
    pause
    exit /b 1
)

REM Запуск теста
python test_price_loading.py

echo.
pause
