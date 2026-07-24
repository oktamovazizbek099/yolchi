@echo off
echo ===================================================
echo 🚀 Starting Django Web Dashboard & Admin Panel...
echo ===================================================
call .\venv\Scripts\activate.bat
python manage.py migrate
python create_superadmin.py
python manage.py runserver 0.0.0.0:8000
pause
