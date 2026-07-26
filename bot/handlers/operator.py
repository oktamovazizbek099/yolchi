from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from apps.main.models import RoleChoices
from bot.handlers.start import BTN_OPERATOR_LOGIN, get_main_keyboard
from bot.utils.db_api import (
    authenticate_operator,
    get_active_drivers,
    get_driver_groups,
    get_pending_announcements,
    get_user_by_telegram_id,
    mark_announcement_broadcasted,
)

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)


class OperatorStates(StatesGroup):
    waiting_for_password = State()


@router.message(F.text == BTN_OPERATOR_LOGIN)
async def start_operator_login(message: Message, state: FSMContext):
    await state.set_state(OperatorStates.waiting_for_password)
    await message.answer(
        "🔐 Web admin bergan operator parolini kiriting:\n\n"
        "(Bekor qilish uchun /start bosing)",
        parse_mode=None,
    )


@router.message(OperatorStates.waiting_for_password, F.text, ~F.text.startswith('/'))
async def process_operator_password(message: Message, state: FSMContext):
    operator = await authenticate_operator(message.from_user.id, message.text or '')

    if not operator:
        await message.answer(
            "❌ Parol xato.\n\nQayta urinib ko'ring yoki /start bosing.",
            parse_mode=None,
        )
        return

    await state.clear()
    await message.answer(
        f"✅ Avtorizatsiyadan o'tdingiz!\n\n"
        f"Operator: {operator.get_full_name() or operator.username}",
        reply_markup=get_main_keyboard(operator),
        parse_mode=None,
    )


@router.message(F.text == "📥 Kutilayotgan E'lonlar")
async def show_pending_announcements(message: Message):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != RoleChoices.OPERATOR:
        await message.answer("Siz operator emassiz.", parse_mode=None)
        return

    pending = await get_pending_announcements()
    if not pending:
        await message.answer(
            "📥 Kutilayotgan buyurtma yo'q.\n\n"
            "Buyurtmalar haydovchilar guruhiga avtomatik yuborilmoqda.",
            parse_mode=None,
        )
        return

    for ann in pending:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="📢 Haydovchilarga Yuborish",
                callback_data=f"send_ann_{ann.id}"
            )
        ]])
        await message.answer(
            f"🆔 Buyurtma #{ann.id}\n\n{ann.formatted_text}",
            reply_markup=kb,
            parse_mode=None,
        )


@router.callback_query(F.data.startswith("send_ann_"))
async def process_send_announcement_callback(callback: CallbackQuery):
    from bot.handlers.group import broadcast_order

    try:
        ann_id = int(callback.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Noto'g'ri tugma.", show_alert=True)
        return

    operator = await get_user_by_telegram_id(callback.from_user.id)
    ann = await mark_announcement_broadcasted(ann_id, operator_user=operator)
    if not ann:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return

    driver_groups = await get_driver_groups()
    # Operator qo'lda yuborganda haydovchilarga shaxsiy ham yuboriladi
    sent = await broadcast_order(callback.bot, ann, driver_groups, also_dm=True)

    try:
        await callback.message.edit_text(
            f"✅ Buyurtma #{ann.id} yuborildi!\n"
            f"Jami manzil: {sent} ta.",
            parse_mode=None,
        )
    except Exception:
        pass
    await callback.answer()


@router.message(F.text == "🚗 Haydovchilar")
async def show_drivers_info(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != RoleChoices.OPERATOR:
        return

    drivers = await get_active_drivers()
    text = f"🚗 Bo'sh haydovchilar: {len(drivers)} ta\n\n"
    for d in drivers[:15]:
        text += f"• {d.first_name or d.username} — {d.phone_number or 'tel yo`q'}\n"
    if len(drivers) > 15:
        text += f"\n... va yana {len(drivers) - 15} ta"

    await message.answer(text, parse_mode=None)


@router.message(F.text == "🚪 Chiqish")
async def process_logout(message: Message, state: FSMContext):
    from asgiref.sync import sync_to_async

    await state.clear()
    user = await get_user_by_telegram_id(message.from_user.id)
    if user and user.role == RoleChoices.OPERATOR:
        user.is_telegram_authenticated = False
        await sync_to_async(user.save)()

    await message.answer(
        "🚪 Siz botdan chiqdingiz.",
        reply_markup=get_main_keyboard(None),
        parse_mode=None,
    )
