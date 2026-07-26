from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from apps.main.models import RoleChoices
from bot.utils.db_api import get_user_by_telegram_id

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)

BTN_OPERATOR_LOGIN = "🔑 Operator sifatida kirish"
BTN_DRIVER_REGISTER = "📲 Haydovchi bo'lib ro'yxatdan o'tish"


def get_main_keyboard(user):
    """Foydalanuvchi roliga qarab asosiy klaviatura."""
    if user and (user.role == RoleChoices.SUPERADMIN or user.is_superuser) \
            and user.is_telegram_authenticated:
        from bot.handlers.superadmin import admin_keyboard
        return admin_keyboard()

    if user and user.role == RoleChoices.OPERATOR and user.is_telegram_authenticated:
        kb = [
            [KeyboardButton(text="📥 Kutilayotgan E'lonlar"), KeyboardButton(text="🚗 Haydovchilar")],
            [KeyboardButton(text="🚪 Chiqish")],
        ]
        return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    if user and user.role == RoleChoices.DRIVER:
        kb = [
            [KeyboardButton(text="📋 Mening buyurtmalarim")],
            [KeyboardButton(text="📞 Telefon raqamni yangilash", request_contact=True)],
        ]
        return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    kb = [
        [KeyboardButton(text=BTN_DRIVER_REGISTER, request_contact=True)],
        [KeyboardButton(text=BTN_OPERATOR_LOGIN)],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user_by_telegram_id(message.from_user.id)

    if user and (user.role == RoleChoices.SUPERADMIN or user.is_superuser) \
            and user.is_telegram_authenticated:
        await message.answer(
            f"👑 Superadmin paneli\n\nXush kelibsiz, {user.get_full_name() or user.username}!",
            reply_markup=get_main_keyboard(user),
            parse_mode=None,
        )
        return

    if user and user.role == RoleChoices.OPERATOR and user.is_telegram_authenticated:
        await message.answer(
            f"Xush kelibsiz, Operator {user.get_full_name() or user.username}!\n"
            "Tizim tayyor. Guruhdan tushgan buyurtmalarni boshqarishingiz mumkin.",
            reply_markup=get_main_keyboard(user),
            parse_mode=None,
        )
        return

    if user and user.role == RoleChoices.DRIVER:
        await message.answer(
            f"Assalomu alaykum, {user.first_name}!\n\n"
            "Siz haydovchi sifatida ro'yxatdan o'tgansiz.\n"
            "Yangi buyurtmalar haydovchilar guruhiga tushadi — birinchi bo'lib "
            "'✅ Zakazni yopish' tugmasini bosgan haydovchi buyurtmani oladi.",
            reply_markup=get_main_keyboard(user),
            parse_mode=None,
        )
        return

    await message.answer(
        "Assalomu alaykum! #2bot Taxi Dispatcher tizimiga xush kelibsiz.\n\n"
        "🚗 Haydovchi bo'lsangiz — pastdagi ro'yxatdan o'tish tugmasini bosing.\n"
        "🎧 Operator bo'lsangiz — 'Operator sifatida kirish' tugmasini bosing.\n"
        "👑 Superadmin bo'lsangiz — /admin buyrug'ini yuboring.",
        reply_markup=get_main_keyboard(None),
        parse_mode=None,
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    is_admin = user and (
        user.role == RoleChoices.SUPERADMIN
        or user.is_superuser
        or (user.role == RoleChoices.OPERATOR and user.is_telegram_authenticated)
    )

    text = (
        "📖 Yordam\n"
        f"{'─' * 22}\n\n"
        "Tizim qanday ishlaydi:\n"
        "1️⃣ Yo'lovchi o'z guruhiga buyurtma yozadi\n"
        "2️⃣ Bot uni ushlab olib haydovchilar guruhiga tashlaydi\n"
        "3️⃣ Birinchi '✅ Zakazni yopish' bosgan haydovchi buyurtmani oladi\n\n"
        "Buyruqlar:\n"
        "  /start — bosh menyu\n"
        "  /help — shu yordam\n"
        "  /admin — superadmin paneli\n\n"
        "Haydovchi bo'lish: /start → telefon raqamni yuborish\n"
        "Operator bo'lish: /start → 'Operator sifatida kirish' → parol"
    )

    if is_admin:
        text += (
            "\n\n"
            "👑 Guruh sozlash buyruqlari (guruh ichida yoziladi):\n"
            "  /yolovchi_guruh — bu guruh yo'lovchilar guruhi bo'ladi\n"
            "  /haydovchi_guruh — bu guruh haydovchilar guruhi bo'ladi\n"
            "  /guruh_ochir — guruhni ro'yxatdan chiqarish\n"
            "  /holat — guruh qanday sozlanganini ko'rish\n"
            "  /id — guruh chat ID sini ko'rish"
        )

    await message.answer(text, parse_mode=None)


@router.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext):
    """Operator sifatida kirish (tugma bilan bir xil)."""
    from bot.handlers.operator import OperatorStates

    await state.set_state(OperatorStates.waiting_for_password)
    await message.answer(
        "🔐 Operator parolini kiriting:\n\n(Bekor qilish uchun /start bosing)",
        parse_mode=None,
    )
