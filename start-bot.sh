#!/bin/sh
# BOT service — faqat Telegram bot (aiogram polling). Gunicorn bu yerda ishga tushmaydi!
#
# MUHIM: bir vaqtda faqat BITTA bot instance ishlashi kerak, aks holda Telegram
# "Conflict: terminated by other getUpdates request" xatosini qaytaradi.
set -e

export PYTHONPATH="${PYTHONPATH}:."

# Migratsiyalarni WEB service bajaradi. Ikkalasi bir vaqtda migrate qilsa
# Postgres'da to'qnashuv bo'lishi mumkin — shuning uchun bot faqat kutadi.
echo "⏳ Migratsiyalar kutilmoqda..."
i=0
while [ $i -lt 40 ]; do
    if python manage.py migrate --check >/dev/null 2>&1; then
        echo "✅ Baza tayyor."
        break
    fi
    i=$((i + 1))
    echo "   ... ($i/40)"
    sleep 3
done

if [ $i -ge 40 ]; then
    echo "⚠️  Migratsiyalar 2 daqiqada tayyor bo'lmadi — baribir ishga tushiryapman."
fi

echo "🤖 Telegram bot ishga tushmoqda..."
exec python bot/main.py
