#!/bin/sh
# ESKIRGAN — bu skript ilgari web va botni BITTA jarayonda ishga tushirardi,
# natijada ikki service ham botni polling qilib Telegram konfliktiga olib kelardi.
#
# Endi ikkita alohida skript bor:
#   start-web.sh — Django + gunicorn
#   start-bot.sh — faqat Telegram bot
#
# Eski sozlamalar buzilmasligi uchun bu fayl xavfsiz variantga (web) yo'naltiradi.
echo "⚠️  start.sh eskirgan — start-web.sh ishga tushirilmoqda."
exec sh start-web.sh
