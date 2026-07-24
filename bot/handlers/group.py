import re
from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.db_api import create_announcement_from_group, get_bot_settings, get_active_drivers, mark_announcement_broadcasted
from apps.main.models import User, RoleChoices
from asgiref.sync import sync_to_async

router = Router()

PHONE_REGEX = re.compile(r'(\+?998[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2})|(\b\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b)')

@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group_message(message: Message):
    if not message.text or message.from_user.is_bot:
        return

    raw_text = message.text
    passenger_name = message.from_user.full_name or message.from_user.first_name
    passenger_tg_id = message.from_user.id
    passenger_username = message.from_user.username
    msg_id = message.message_id

    # Phone extraction from text using Regex
    extracted_phone = None
    match = PHONE_REGEX.search(raw_text)
    if match:
        extracted_phone = match.group(0).replace(' ', '').replace('-', '')

    # Create announcement record in DB
    ann = await create_announcement_from_group(
        passenger_name=passenger_name,
        passenger_tg_id=passenger_tg_id,
        passenger_username=passenger_username,
        raw_text=raw_text,
        group_msg_id=msg_id
    )

    if extracted_phone:
        ann.passenger_phone = extracted_phone
        from asgiref.sync import sync_to_async
        await sync_to_async(ann.save)()

    settings = await get_bot_settings()

    if settings.auto_broadcast:
        # Auto broadcast mode enabled
        await mark_announcement_broadcasted(ann.id)
        drivers = await get_active_drivers()

        contact_info = f"\n\n📞 **Bog'lanish:** {extracted_phone or '@' + (passenger_username or '') or 'Telefon ko\'rsatilmadi'}"
        msg_to_send = ann.formatted_text + contact_info

        for driver in drivers:
            try:
                await message.bot.send_message(
                    chat_id=driver.telegram_id,
                    text=msg_to_send,
                    parse_mode="Markdown"
                )
            except Exception:
                pass
    else:
        # Notify logged in operators about pending announcement
        @sync_to_async
        def get_logged_in_operators():
            return list(User.objects.filter(role=RoleChoices.OPERATOR, is_telegram_authenticated=True, telegram_id__isnull=False))

        operators = await get_logged_in_operators()
        
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📢 Haydovchilarga Yuborish", 
                callback_data=f"send_ann_{ann.id}"
            )]
        ])

        phone_str = f"\n📞 **Tel:** {extracted_phone}" if extracted_phone else ""
        notify_msg = f"🔔 **Guruhdan Yangi E'lon Keldi!** (E'lon #{ann.id}){phone_str}\n\n{ann.formatted_text}"

        for op in operators:
            try:
                await message.bot.send_message(
                    chat_id=op.telegram_id,
                    text=notify_msg,
                    reply_markup=inline_kb,
                    parse_mode="Markdown"
                )
            except Exception:
                pass
