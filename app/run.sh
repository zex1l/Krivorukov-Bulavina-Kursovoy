#!/bin/bash

echo
echo "==================================="
echo "Трекер расходов - запуск приложения"
echo "==================================="
echo

# Проверяем, установлены ли зависимости
echo "Проверка зависимостей..."
python3 -m pip show flask > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "Flask не установлен. Устанавливаю зависимости..."
    python3 -m pip install -r requirements.txt
else
    echo "Зависимости уже установлены."
fi

echo
echo "Запускаю приложение..."
echo "Откройте браузер и перейдите по адресу:"
echo "http://127.0.0.1:5000"
echo
echo "Для остановки приложения нажмите Ctrl+C"
echo

python3 app.py
