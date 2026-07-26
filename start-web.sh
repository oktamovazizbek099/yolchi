#!/bin/sh
# WEB service — faqat Django (gunicorn). Bot bu yerda ishga tushmaydi!
# Migratsiyalar va boshlang'ich foydalanuvchilar shu servisda bajariladi.
set -e

export PYTHONPATH="${PYTHONPATH}:."

echo "🗄  Migratsiyalar bajarilmoqda..."
python manage.py migrate --noinput

echo "📦 Statik fayllar yig'ilmoqda..."
python manage.py collectstatic --noinput

echo "👤 Boshlang'ich foydalanuvchilar tekshirilmoqda..."
python create_superadmin.py

echo "🌐 Gunicorn ishga tushmoqda (port ${PORT:-8000})..."
exec gunicorn core.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
