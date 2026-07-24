from aiogram import Router, F
from aiogram.types import Message
from bot.utils.db_api import register_or_update_driver, get_user_by_telegram_id
from bot.handlers.start import get_main_keyboard
from asgiref.sync import sync_to_async

router = Router()

@router.message(F.contact)
async def process_driver_contact(message: Message):
    contact = message.contact
    telegram_id = message.from_user.id
    phone = contact.phone_number
    first_name = contact.first_name or message.from_user.first_name

    driver = await register_or_update_driver(telegram_id, phone, first_name)

    await message.answer(
        f"✅ Rahmat **{first_name}**!\n"
        f"Siz **Haydovchi** sifatida ro'yxatdan o'tdingiz.\n"
        f"Telefon: `{phone}`\n\n"
        f"Endi guruhdan tushgan yo'lovchi e'lonlari sizga shu bot orqali avtomatik kelib turadi.",
        reply_markup=get_main_keyboard(driver),
        parse_mode="Markdown"
    )

@router.message(F.text == "🟢 Status: Bo'shman")
async def set_driver_available(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if user:
        user.is_driver_active = True
        await sync_to_async(user.save)()
        await message.answer("Sizning statusingiz **Aktiv (Bo'shman)** ga o'zgartirildi. Yangi e'lonlarni qabul qilasiz.", parse_mode="Markdown")

@router.message(F.text == "🔴 Status: Bandman")
async def set_driver_busy(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if user:
        user.is_driver_active = False
        await sync_to_async(user.save)()
        await message.answer("Sizning statusingiz **Bandman** ga o'zgartirildi. Vaqtincha e'lonlar kelmaydi.", parse_mode="Markdown")
