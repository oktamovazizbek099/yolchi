"""
Guruh ichida ishlatiladigan sozlash buyruqlari.
Faqat superadmin yoki avtorizatsiyadan o'tgan operator ishlata oladi.

  /yolovchi_guruh   -> bu guruhni YO'LOVCHILAR guruhi qilib belgilash (bot o'qiydi)
  /haydovchi_guruh  -> bu guruhni HAYDOVCHILAR guruhi qilib belgilash (bot yozadi)
  /guruh_ochir      -> bu guruhni ro'yxatdan chiqarish
  /id               -> guruh chat_id sini ko'rsatish
  /holat            -> bu guruh qanday sozlanganini ko'rsatish

Bu router group.py dan OLDIN ro'yxatga olinadi, aks holda buyruqlar
buyurtma tinglovchisiga tushib ketardi.
"""
import logging

from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

from apps.main.models import GroupType
from bot.utils.db_api import get_group, is_admin_user, register_group, unregister_group

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))

NO_ACCESS = (
    "⛔️ Bu buyruq faqat superadmin va operatorlar uchun.\n\n"
    "Avval botga shaxsiy yozib /admin (yoki operator paroli) orqali kiring."
)


async def _require_admin(message: Message):
    if message.from_user is None:
        return None
    user = await is_admin_user(message.from_user.id)
    if user is None:
        await message.reply(NO_ACCESS)
        return None
    return user


@router.message(Command("id"))
async def cmd_chat_id(message: Message):
    await message.reply(
        f"🆔 Guruh ma'lumotlari\n\n"
        f"Nomi: {message.chat.title}\n"
        f"Chat ID: {message.chat.id}\n"
        f"Turi: {message.chat.type}",
        parse_mode=None,
    )


@router.message(Command("yolovchi_guruh"))
async def cmd_set_passenger_group(message: Message):
    user = await _require_admin(message)
    if not user:
        return

    group, created, old_type = await register_group(
        chat_id=message.chat.id,
        title=message.chat.title or '',
        group_type=GroupType.PASSENGER,
        added_by=user,
    )

    if created:
        text = "✅ Bu guruh YO'LOVCHILAR guruhi sifatida ro'yxatga olindi."
    elif old_type != GroupType.PASSENGER:
        text = "🔄 Guruh turi HAYDOVCHILAR dan YO'LOVCHILAR ga o'zgartirildi."
    else:
        text = "ℹ️ Bu guruh allaqachon YO'LOVCHILAR guruhi (qayta aktivlashtirildi)."

    await message.reply(
        f"{text}\n\n"
        f"📍 {message.chat.title}\n"
        f"🆔 {message.chat.id}\n\n"
        f"Endi bu yerga yozilgan buyurtmalar haydovchilar guruhiga avtomatik yuboriladi.",
        parse_mode=None,
    )


@router.message(Command("haydovchi_guruh"))
async def cmd_set_driver_group(message: Message):
    user = await _require_admin(message)
    if not user:
        return

    group, created, old_type = await register_group(
        chat_id=message.chat.id,
        title=message.chat.title or '',
        group_type=GroupType.DRIVER,
        added_by=user,
    )

    if created:
        text = "✅ Bu guruh HAYDOVCHILAR guruhi sifatida ro'yxatga olindi."
    elif old_type != GroupType.DRIVER:
        text = "🔄 Guruh turi YO'LOVCHILAR dan HAYDOVCHILAR ga o'zgartirildi."
    else:
        text = "ℹ️ Bu guruh allaqachon HAYDOVCHILAR guruhi (qayta aktivlashtirildi)."

    await message.reply(
        f"{text}\n\n"
        f"📍 {message.chat.title}\n"
        f"🆔 {message.chat.id}\n\n"
        f"Buyurtmalar shu yerga tashlanadi. Bot bu guruhdagi yozishmalarni "
        f"buyurtma deb hisoblamaydi.\n\n"
        f"⚠️ Bot bu guruhda xabar yubora olishi kerak (admin qilib qo'ying).",
        parse_mode=None,
    )


@router.message(Command("guruh_ochir"))
async def cmd_unset_group(message: Message):
    user = await _require_admin(message)
    if not user:
        return

    removed = await unregister_group(message.chat.id)
    if removed:
        await message.reply(
            "🗑 Guruh ro'yxatdan chiqarildi. Bot endi bu guruhga umuman e'tibor bermaydi.",
            parse_mode=None,
        )
    else:
        await message.reply("ℹ️ Bu guruh ro'yxatda yo'q edi.", parse_mode=None)


@router.message(Command("holat"))
async def cmd_group_status(message: Message):
    group = await get_group(message.chat.id)

    if group is None:
        await message.reply(
            "⚪️ Bu guruh ro'yxatda yo'q — bot bu yerdagi xabarlarni e'tiborsiz qoldiradi.\n\n"
            "Sozlash uchun (admin):\n"
            "  /yolovchi_guruh — buyurtmalar shu yerdan olinadi\n"
            "  /haydovchi_guruh — buyurtmalar shu yerga yuboriladi",
            parse_mode=None,
        )
        return

    holat = "🟢 Aktiv" if group.is_active else "🔴 O'chirilgan"
    turi = (
        "📥 YO'LOVCHILAR guruhi (bot o'qiydi)"
        if group.group_type == GroupType.PASSENGER
        else "📤 HAYDOVCHILAR guruhi (bot yozadi)"
    )

    await message.reply(
        f"{turi}\n{holat}\n\n"
        f"📍 {group.title or message.chat.title}\n"
        f"🆔 {group.chat_id}",
        parse_mode=None,
    )
