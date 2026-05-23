@echo off
chcp 65001 >nul
echo.
echo ===================================
echo Трекер расходов - запуск приложения
echo ===================================
echo.

REM Проверяем, установлены ли зависимости
echo Проверка зависимостей...
python -m pip show flask >nul 2>&1
if errorlevel 1 (
    echo Flask не установлен. Устанавливаю зависимости...
    python -m pip install -r requirements.txt
) else (
    echo Зависимости уже установлены.
)

echo.
echo Запускаю приложение...
echo Откройте браузер и перейдите по адресу:
echo http://127.0.0.1:5000
echo.
echo Для остановки приложения нажмите Ctrl+C
echo.

python app.py
pause
