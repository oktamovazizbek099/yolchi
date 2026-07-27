#!/bin/sh
# Yagona kirish nuqtasi. Qaysi rolda ishlashi SERVICE_ROLE bilan aniqlanadi:
#
#   SERVICE_ROLE=bot  -> faqat Telegram bot (aiogram polling)
#   SERVICE_ROLE=web  -> faqat Django + gunicorn (standart)
#
# MUHIM: bir vaqtda faqat BITTA service SERVICE_ROLE=bot bo'lishi kerak,
# aks holda Telegram "Conflict: terminated by other getUpdates request" beradi.
#
# Railway'da har bir service uchun start command'ni alohida sozlash imkoni
# bo'lmagani uchun shu usul tanlandi — ikkala service ham shu skriptni
# ishga tushiradi, lekin har biri o'z rolini bajaradi.

ROLE="${SERVICE_ROLE:-web}"

case "$ROLE" in
    bot)
        echo "🤖 Rol: BOT"
        exec sh start-bot.sh
        ;;
    web)
        echo "🌐 Rol: WEB"
        exec sh start-web.sh
        ;;
    *)
        echo "❌ Noma'lum SERVICE_ROLE='$ROLE'. 'web' yoki 'bot' bo'lishi kerak."
        echo "   Xavfsizlik uchun web rejimida ishga tushiryapman (bot ishga tushmaydi)."
        exec sh start-web.sh
        ;;
esac
