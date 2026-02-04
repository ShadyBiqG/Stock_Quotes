@echo off
chcp 65001 >nul
cls

REM Переход в корневую директорию проекта
cd /d "%~dp0\.."

echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║           🔍 Проверка проекта Stock Quotes 🔍                ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

python scripts\verify_project.py

echo.
pause
