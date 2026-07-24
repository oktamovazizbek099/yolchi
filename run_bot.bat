@echo off
echo ===================================================
echo 🤖 Starting Telegram Bot (#2bot Taxi Dispatcher)...
echo ===================================================
call .\venv\Scripts\activate.bat
python bot/main.py
pause
