from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from bot.utils.db_api import get_user_by_telegram_id
from apps.main.models import RoleChoices

router = Router()

def get_main_keyboard(user):
    if user and user.role == RoleChoices.OPERATOR and user.is_telegram_authenticated:
        kb = [
            [KeyboardButton(text="📥 Kutilayotgan E'lonlar"), KeyboardButton(text="🚗 Haydovchilar")],
            [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="🚪 Chiqish")]
        ]
        return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    elif user and user.role == RoleChoices.DRIVER:
        kb = [
            [KeyboardButton(text="🟢 Status: Bo'shman"), KeyboardButton(text="🔴 Status: Bandman")],
            [KeyboardButton(text="📞 Telefon raqamni yangilash", request_contact=True)]
        ]
        return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    else:
        kb = [
            [KeyboardButton(text="📲 Haydovchi bo'lib ro'yxatdan o'tish", request_contact=True)],
            [KeyboardButton(text="🔑 Operator sifida kirish")]
        ]
        return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user_by_telegram_id(message.from_user.id)
    
    if user and user.role == RoleChoices.OPERATOR and user.is_telegram_authenticated:
        await message.answer(
            f"Xush kelibsiz, Operator **{user.get_full_name() or user.username}**!\n"
            "Tizim tayyor. Guruhdan tushgan e'lonlarni boshqarishingiz mumkin.",
            reply_markup=get_main_keyboard(user),
            parse_mode="Markdown"
        )
    elif user and user.role == RoleChoices.DRIVER:
        await message.answer(
            f"Assalomu alaykum, Haydovchi **{user.first_name}**!\n"
            "Siz tizimda ro'yxatdan o'tgansiz. Guruhdan yangi yo'lovchi e'lonlari tushishi bilan sizga yuboriladi.",
            reply_markup=get_main_keyboard(user),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "Assalomu alaykum! **#2bot Taxi Dispatcher** tizimiga xush kelibsiz.\n\n"
            "• Agar **Haydovchi** bo'lsangiz: pastdagi *'Haydovchi bo'lib ro'yxatdan o'tish'* tugmasini bosing.\n"
            "• Agar **Operator** bo'lsangiz: *'Operator sifatida kirish'* tugmasini bosib, Web admin bergan parolni kiriting.",
            reply_markup=get_main_keyboard(None),
            parse_mode="Markdown"
        )
