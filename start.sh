#!/bin/sh

echo "🚀 Executing Railway Startup Commands..."

export PYTHONPATH=$PYTHONPATH:.

# Run database migrations
python manage.py migrate --noinput

# Collect static files for Django Admin & Dashboard
python manage.py collectstatic --noinput

# Seed superadmin and initial operator
python create_superadmin.py

# Start Telegram Bot in background
echo "🤖 Starting Telegram Bot runner in background..."
python bot/main.py &

# Start Web Gunicorn server on Railway assigned PORT
echo "🌐 Starting Django Web Server with Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000}
