from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import Message

from apps.main.models import RoleChoices
from bot.handlers.group import build_contact_keyboard
from bot.handlers.start import get_main_keyboard
from bot.utils.db_api import (
    build_private_order_text,
    get_driver_orders,
    register_or_update_driver,
)

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)


@router.message(F.contact)
async def process_driver_contact(message: Message):
    """
    Kontakt yuborilganda haydovchi sifatida ro'yxatga olish.
    Operator/superadminning roli o'zgartirilmaydi — faqat telefoni yangilanadi.
    """
    contact = message.contact

    # Boshqa odamning kontaktini yuborishni oldini olish
    if contact.user_id and contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ Iltimos, o'zingizning telefon raqamingizni yuboring "
            "(tugma orqali), boshqa odamnikini emas.",
            parse_mode=None,
        )
        return

    user, created = await register_or_update_driver(
        telegram_id=message.from_user.id,
        phone_number=contact.phone_number,
        full_name=contact.first_name or message.from_user.first_name,
    )

    if user.role in (RoleChoices.SUPERADMIN, RoleChoices.OPERATOR):
        await message.answer(
            f"✅ Telefon raqamingiz yangilandi: {contact.phone_number}\n\n"
            f"Rolingiz o'zgarmadi ({user.get_role_display()}).",
            reply_markup=get_main_keyboard(user),
            parse_mode=None,
        )
        return

    if created:
        text = (
            f"✅ Rahmat, {user.first_name}!\n\n"
            f"Siz haydovchi sifatida ro'yxatdan o'tdingiz.\n"
            f"📞 Telefon: {contact.phone_number}\n\n"
            f"Endi haydovchilar guruhidagi buyurtmalarni qabul qila olasiz."
        )
    else:
        text = (
            f"✅ Ma'lumotlaringiz yangilandi.\n"
            f"📞 Telefon: {contact.phone_number}"
        )

    await message.answer(text, reply_markup=get_main_keyboard(user), parse_mode=None)


@router.message(F.text == "📋 Mening buyurtmalarim")
async def show_my_orders(message: Message):
    """Haydovchi qabul qilgan oxirgi buyurtmalar — aloqa ma'lumotlari bilan."""
    orders = await get_driver_orders(message.from_user.id, limit=5)

    if not orders:
        await message.answer(
            "📋 Siz hali birorta buyurtma qabul qilmagansiz.\n\n"
            "Haydovchilar guruhidagi buyurtmada '✅ Zakazni yopish' tugmasini "
            "birinchi bo'lib bosgan haydovchi buyurtmani oladi.",
            parse_mode=None,
        )
        return

    await message.answer(
        f"📋 Sizning oxirgi {len(orders)} ta buyurtmangiz:", parse_mode=None
    )
    for ann in orders:
        await message.answer(
            build_private_order_text(ann),
            reply_markup=build_contact_keyboard(ann),
            parse_mode=None,
        )
