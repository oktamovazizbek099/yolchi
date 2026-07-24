import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from bot.config import BOT_TOKEN
from bot.handlers import routers

logging.basicConfig(level=logging.INFO)

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish / Bosh menyu"),
        BotCommand(command="login", description="Operator sifatida tizimga kirish"),
        BotCommand(command="help", description="Yordam va yo'riqnoma"),
    ]
    await bot.set_my_commands(commands)

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "7777777777:CHANGE_ME_IN_ENV":
        print("❌ XATOLIK: .env faylida BOT_TOKEN kiritilmagan! Iltimos, Telegram Bot Tokeningizni .env fayliga yozing.")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Register all handlers
    for r in routers:
        dp.include_router(r)

    # Set bot commands menu in Telegram UI
    try:
        await setup_bot_commands(bot)
        bot_info = await bot.get_me()
        print(f"✅ BOT ULANIB ISHGA TUSHDI: @{bot_info.username} ({bot_info.first_name})")
    except Exception as e:
        print(f"⚠️ Bot buyruqlarini sozlashda ogohlantirish: {e}")

    print("🚀 #2bot Telegram Bot polling rejimida ishlamoqda...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
