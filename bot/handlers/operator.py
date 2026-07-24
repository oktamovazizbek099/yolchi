from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.utils.db_api import (
    authenticate_operator, 
    get_user_by_telegram_id, 
    get_pending_announcements, 
    mark_announcement_broadcasted, 
    get_active_drivers
)
from apps.main.models import RoleChoices
from bot.handlers.start import get_main_keyboard

router = Router()

class OperatorStates(StatesGroup):
    waiting_for_password = State()

@router.message(F.text == "🔑 Operator sifida kirish")
async def start_operator_login(message: Message, state: FSMContext):
    await state.set_state(OperatorStates.waiting_for_password)
    await message.answer(
        "🔐 Web Admin panel tomonidan sizga berilgan **Operator Parolini** kiriting:"
    )

@router.message(OperatorStates.waiting_for_password)
async def process_operator_password(message: Message, state: FSMContext):
    password = message.text
    telegram_id = message.from_user.id
    
    operator = await authenticate_operator(telegram_id, password)
    if operator:
        await state.clear()
        await message.answer(
            f"✅ Muvaffaqiyatli avtorizatsiyadan o'tdingiz!\n\n"
            f"Operator: **{operator.get_full_name() or operator.username}**",
            reply_markup=get_main_keyboard(operator),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❌ **Xato parol!** Parol Web Admin panelda superadmin tomonidan berilgan bo'lishi kerak.\n\n"
            "Qayta urunib ko'ring yoki /start bosing."
        )

@router.message(F.text == "📥 Kutilayotgan E'lonlar")
async def show_pending_announcements(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != RoleChoices.OPERATOR:
        await message.answer("Siz operator emassiz.")
        return

    pending = await get_pending_announcements()
    if not pending:
        await message.answer("📥 Hozircha kutilayotgan yangi e'lonlar yo'q.")
        return

    for ann in pending:
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📢 Haydovchilarga Yuborish", 
                callback_query="dummy",
                callback_data=f"send_ann_{ann.id}"
            )]
        ])
        await message.answer(
            f"🆔 **E'lon #{ann.id}**\n\n{ann.formatted_text}",
            reply_markup=inline_kb,
            parse_mode="Markdown"
        )

@router.callback_query(F.data.startswith("send_ann_"))
async def process_send_announcement_callback(callback: CallbackQuery):
    ann_id = int(callback.data.split("_")[2])
    operator = await get_user_by_telegram_id(callback.from_user.id)
    
    ann = await mark_announcement_broadcasted(ann_id, operator_user=operator)
    if not ann:
        await callback.answer("E'lon topilmadi yoki allaqachon yuborilgan.", show_alert=True)
        return

    drivers = await get_active_drivers()
    sent_count = 0

    contact_text = f"\n\n📞 **Bog'lanish:** {ann.passenger_phone or '@' + (ann.passenger_username or '') or 'Telefon ko\'rsatilmagan'}"
    full_broadcast_msg = ann.formatted_text + contact_text

    for driver in drivers:
        try:
            await callback.bot.send_message(
                chat_id=driver.telegram_id,
                text=full_broadcast_msg,
                parse_mode="Markdown"
            )
            sent_count += 1
        except Exception as e:
            pass

    await callback.message.edit_text(
        f"✅ **E'lon #{ann.id} haydovchilarga yuborildi!**\n"
        f"Jami yuborilgan haydovchilar soni: **{sent_count}** ta.",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(F.text == "🚗 Haydovchilar")
async def show_drivers_info(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != RoleChoices.OPERATOR:
        return
        
    drivers = await get_active_drivers()
    text = f"🚗 **Aktiv Haydovchilar Soni:** {len(drivers)} ta\n\n"
    for d in drivers[:15]:
        text += f"• {d.first_name or d.username} - 📞 {d.phone_number or 'Noma\'lum'}\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "🚪 Chiqish")
async def process_logout(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user_by_telegram_id(message.from_user.id)
    if user:
        user.is_telegram_authenticated = False
        user.telegram_id = None
        from asgiref.sync import sync_to_async
        await sync_to_async(user.save)()
        
    await message.answer("Siz botdan chiqdingiz.", reply_markup=get_main_keyboard(None))
