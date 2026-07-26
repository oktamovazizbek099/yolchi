"""
Yo'lovchilar guruhi -> Haydovchilar guruhi oqimi.

MUHIM: bot faqat ro'yxatdan o'tgan va AKTIV "PASSENGER" guruhlaridan xabar oladi.
Haydovchilar guruhi va ro'yxatda yo'q guruhlar butunlay e'tiborsiz qoldiriladi,
shuning uchun haydovchilarning o'zaro yozishmalari buyurtmaga aylanmaydi.
"""
import logging

from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async

from apps.main.models import User, RoleChoices
from bot.utils.db_api import (
    accept_order,
    build_private_order_text,
    create_announcement_from_group,
    get_accepted_driver_tg_id,
    get_active_drivers,
    get_announcement,
    get_bot_settings,
    get_broadcast_messages,
    get_driver_groups,
    get_source_group,
    mark_announcement_broadcasted,
    save_broadcast_message,
)
from bot.utils.filters import is_order_message

logger = logging.getLogger(__name__)

router = Router()

ACCEPT_MARKER = "🔴 BUYURTMANI QO'LGA KIRITISH UCHUN TEZROQ HARAKAT QILING!!!"


# ========================================
# TUGMALAR
# ========================================

def build_order_keyboard(ann_id):
    """
    GURUHDAGI buyurtma tugmasi — faqat bitta.
    Aloqa tugmalari bu yerda YO'Q: yo'lovchining profili va raqami faqat
    buyurtmani olgan haydovchiga shaxsiy xabarda beriladi.
    """
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Zakazni yopish",
            callback_data=f"accept_order_{ann_id}"
        )
    ]])


def build_accepted_keyboard(ann_id, driver_name):
    """Qabul qilingandan keyin guruhda qoladigan tugma."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"✅ {driver_name} qabul qildi",
            callback_data=f"already_accepted_{ann_id}"
        )
    ]])


def build_contact_keyboard(ann):
    """
    Buyurtmani olgan haydovchiga SHAXSIY yuboriladigan aloqa tugmalari.
    Bu klaviatura faqat o'sha haydovchining shaxsiy chatida bo'ladi.
    """
    buttons = []

    if ann.passenger_telegram_id:
        buttons.append([InlineKeyboardButton(
            text="🚕 Profilga o'tish",
            url=f"tg://user?id={ann.passenger_telegram_id}"
        )])

    if ann.passenger_phone:
        # Telegram inline tugmada tel: sxemasiga ruxsat bermaydi —
        # raqam callback orqali alert'da ko'rsatiladi.
        buttons.append([InlineKeyboardButton(
            text="🏘 Qo'ng'iroq qilish",
            callback_data=f"show_phone_{ann.id}"
        )])

    if ann.passenger_username:
        buttons.append([InlineKeyboardButton(
            text="📝 Xabarga o'tish",
            url=f"https://t.me/{ann.passenger_username}"
        )])

    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ========================================
# TARQATISH
# ========================================

async def broadcast_order(bot, ann, driver_groups, also_dm=False):
    """
    Buyurtmani barcha aktiv haydovchilar guruhlariga (va ixtiyoriy ravishda
    haydovchilarga shaxsiy) yuborish. Har bir nusxa keyin tahrirlash uchun saqlanadi.
    Returns: yuborilgan nusxalar soni.
    """
    keyboard = build_order_keyboard(ann.id)
    sent = 0

    for group in driver_groups:
        try:
            msg = await bot.send_message(
                chat_id=group.chat_id,
                text=ann.formatted_text,
                reply_markup=keyboard,
                parse_mode=None,
            )
            await save_broadcast_message(ann.id, group.chat_id, msg.message_id, is_group=True)
            sent += 1
        except Exception as e:
            logger.error(f"❌ #{ann.id} -> guruh {group.chat_id} ga yuborilmadi: {e}")

    if also_dm:
        drivers = await get_active_drivers()
        for driver in drivers:
            try:
                msg = await bot.send_message(
                    chat_id=driver.telegram_id,
                    text=ann.formatted_text,
                    reply_markup=keyboard,
                    parse_mode=None,
                )
                await save_broadcast_message(ann.id, driver.telegram_id, msg.message_id, is_group=False)
                sent += 1
            except Exception:
                # Haydovchi botni bloklagan bo'lishi mumkin — jim o'tkazamiz
                pass

    return sent


async def notify_operators(bot, ann):
    """Haydovchilar guruhi sozlanmagan bo'lsa — operatorlarga qo'lda yuborish taklifi."""
    @sync_to_async
    def _operators():
        return list(User.objects.filter(
            role=RoleChoices.OPERATOR,
            is_telegram_authenticated=True,
            telegram_id__isnull=False,
        ))

    operators = await _operators()
    if not operators:
        logger.warning(
            f"⚠️ #{ann.id}: haydovchilar guruhi sozlanmagan va aktiv operator yo'q — "
            f"buyurtma hech kimga yuborilmadi."
        )
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📢 Haydovchilarga Yuborish", callback_data=f"send_ann_{ann.id}")
    ]])

    text = f"🔔 Yangi buyurtma keldi (#{ann.id})\n\n{ann.formatted_text}"

    for op in operators:
        try:
            await bot.send_message(chat_id=op.telegram_id, text=text,
                                   reply_markup=kb, parse_mode=None)
        except Exception:
            pass


# ========================================
# YO'LOVCHILAR GURUHI TINGLOVCHISI
# ========================================

@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}), F.text)
async def handle_group_message(message: Message):
    """Faqat ro'yxatdagi aktiv yo'lovchilar guruhidagi xabarlarni qayta ishlaydi."""
    if message.from_user is None or message.from_user.is_bot:
        return

    chat_id = message.chat.id

    # 1) Guruh ro'yxatda va PASSENGER turidami?
    source_group = await get_source_group(chat_id)
    if source_group is None:
        # Haydovchilar guruhi yoki notanish guruh — hech narsa qilmaymiz
        return

    raw_text = message.text.strip()
    settings = await get_bot_settings()

    # 2) Aqlli filtr
    ok, reason = is_order_message(
        raw_text,
        min_length=settings.min_order_length or 10,
        smart=settings.smart_filter,
    )
    if not ok:
        logger.info(f"⏭ O'tkazib yuborildi ({reason}): {raw_text[:40]!r}")
        return

    # 3) Buyurtma yaratish
    ann = await create_announcement_from_group(
        passenger_name=message.from_user.full_name or message.from_user.first_name,
        passenger_tg_id=message.from_user.id,
        passenger_username=message.from_user.username,
        raw_text=raw_text,
        group_msg_id=message.message_id,
        source_group_id=chat_id,
        source_group_name=source_group.title or message.chat.title,
    )

    # 4) Haydovchilar guruhlariga tarqatish
    driver_groups = await get_driver_groups()

    if not driver_groups and not settings.auto_broadcast:
        await notify_operators(message.bot, ann)
        return

    sent = await broadcast_order(
        message.bot, ann, driver_groups, also_dm=settings.auto_broadcast
    )

    if sent:
        await mark_announcement_broadcasted(ann.id)
        logger.info(f"✅ Buyurtma #{ann.id} {sent} ta manzilga yuborildi")
    else:
        logger.error(f"❌ Buyurtma #{ann.id} hech qayerga yuborilmadi")
        await notify_operators(message.bot, ann)


# ========================================
# BUYURTMANI QABUL QILISH
# ========================================

@router.callback_query(F.data.startswith("accept_order_"))
async def handle_accept_order(callback: CallbackQuery):
    """Haydovchi '✅ Zakazni yopish' tugmasini bosganda."""
    try:
        ann_id = int(callback.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Noto'g'ri tugma.", show_alert=True)
        return

    driver_tg_id = callback.from_user.id
    driver_name = callback.from_user.full_name or callback.from_user.first_name

    ann, driver, already_taken_by = await accept_order(ann_id, driver_tg_id)

    if ann is None:
        await callback.answer("❌ Buyurtma topilmadi!", show_alert=True)
        return

    if already_taken_by:
        taken_name = already_taken_by.first_name or already_taken_by.username or "Noma'lum"
        await callback.answer(
            f"⚠️ Bu buyurtmani allaqachon {taken_name} olgan!",
            show_alert=True
        )
        return

    if driver is None:
        await callback.answer(
            "❌ Siz haydovchi sifatida ro'yxatdan o'tmagansiz!\n\n"
            "Botga shaxsiy yozing va /start bosib telefon raqamingizni yuboring.",
            show_alert=True
        )
        return

    # --- Muvaffaqiyatli qabul qilindi ---
    # Guruhdagi matnda ham aloqa ma'lumoti yo'q — faqat kim olgani yoziladi.
    accepted_text = ann.formatted_text.replace(
        "🔒 Aloqa ma'lumotlari buyurtmani olgan haydovchiga yuboriladi.\n\n", ""
    ).replace(
        ACCEPT_MARKER,
        f"✅ BUYURTMA QABUL QILINDI!\n👤 Haydovchi: {driver_name}"
    )
    new_keyboard = build_accepted_keyboard(ann.id, driver_name)

    # 1) Barcha yuborilgan nusxalarni tahrirlash (bir nechta guruh bo'lishi mumkin)
    broadcasts = await get_broadcast_messages(ann.id)
    edited_current = False

    for bm in broadcasts:
        try:
            await callback.bot.edit_message_text(
                chat_id=bm.chat_id,
                message_id=bm.message_id,
                text=accepted_text,
                reply_markup=new_keyboard,
                parse_mode=None,
            )
            if (callback.message and bm.chat_id == callback.message.chat.id
                    and bm.message_id == callback.message.message_id):
                edited_current = True
        except Exception as e:
            logger.debug(f"#{ann.id} nusxasini tahrirlab bo'lmadi ({bm.chat_id}): {e}")

    # Nusxa saqlanmagan holat uchun zaxira
    if not edited_current and callback.message:
        try:
            await callback.message.edit_text(
                text=accepted_text, reply_markup=new_keyboard, parse_mode=None
            )
        except Exception:
            pass

    # 2) Faqat shu haydovchiga — yo'lovchining to'liq aloqa ma'lumotlari
    dm_ok = True
    try:
        await callback.bot.send_message(
            chat_id=driver_tg_id,
            text=build_private_order_text(ann),
            reply_markup=build_contact_keyboard(ann),
            parse_mode=None,
        )
    except Exception as e:
        dm_ok = False
        logger.warning(f"#{ann.id}: haydovchi {driver_tg_id} ga shaxsiy xabar yuborilmadi: {e}")

    # 3) Yo'lovchiga xabar (bot bilan yozishmagan bo'lsa jim o'tadi)
    if ann.passenger_telegram_id:
        try:
            await callback.bot.send_message(
                chat_id=ann.passenger_telegram_id,
                text=(
                    f"🎉 Sizning buyurtmangiz qabul qilindi!\n\n"
                    f"🚕 Haydovchi: {driver_name}\n"
                    f"Tez orada siz bilan bog'lanishadi."
                ),
                parse_mode=None,
            )
        except Exception:
            pass

    if dm_ok:
        await callback.answer(
            f"✅ Buyurtma #{ann.id} sizniki!\n\n"
            f"Mijozning telefoni va profili sizga shaxsiy xabarda yuborildi.",
            show_alert=True
        )
    else:
        # Haydovchi bot bilan yozishmagan — shaxsiy xabar yubora olmaymiz
        await callback.answer(
            f"✅ Buyurtma #{ann.id} sizniki!\n\n"
            f"⚠️ Lekin aloqa ma'lumotlarini yubora olmadim — botga shaxsiy "
            f"yozib /start bosing, keyin qayta urinib ko'ring.",
            show_alert=True
        )


@router.callback_query(F.data.startswith("already_accepted_"))
async def handle_already_accepted(callback: CallbackQuery):
    """
    Qabul qilingan buyurtma tugmasi.
    Agar bosgan odam — buyurtmani olgan haydovchining o'zi bo'lsa, aloqa
    ma'lumotlarini qayta yuboramiz (masalan birinchi marta yuborilmay qolgan bo'lsa).
    Boshqalarga hech qanday ma'lumot ko'rsatilmaydi.
    """
    try:
        ann_id = int(callback.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("✅ Bu buyurtma allaqachon qabul qilingan.", show_alert=True)
        return

    ann = await get_announcement(ann_id)
    if ann is None:
        await callback.answer("❌ Buyurtma topilmadi.", show_alert=True)
        return

    owner_tg_id = await get_accepted_driver_tg_id(ann_id)

    if owner_tg_id != callback.from_user.id:
        await callback.answer("✅ Bu buyurtmani boshqa haydovchi olgan.", show_alert=True)
        return

    # Egasi — aloqa ma'lumotlarini qayta yuboramiz
    try:
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=build_private_order_text(ann),
            reply_markup=build_contact_keyboard(ann),
            parse_mode=None,
        )
        await callback.answer(
            "📩 Aloqa ma'lumotlari shaxsiy xabarga qayta yuborildi.", show_alert=True
        )
    except Exception:
        await callback.answer(
            "⚠️ Sizga shaxsiy xabar yubora olmadim.\n\n"
            "Botga shaxsiy yozib /start bosing, keyin qayta urinib ko'ring.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("show_phone_"))
async def handle_show_phone(callback: CallbackQuery):
    """
    Telefon raqamini alert'da ko'rsatish.
    Faqat buyurtmani qabul qilgan haydovchi ko'ra oladi.
    """
    try:
        ann_id = int(callback.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Noto'g'ri tugma.", show_alert=True)
        return

    owner_tg_id = await get_accepted_driver_tg_id(ann_id)
    if owner_tg_id != callback.from_user.id:
        await callback.answer(
            "⛔️ Bu ma'lumot faqat buyurtmani olgan haydovchiga ko'rinadi.",
            show_alert=True
        )
        return

    ann = await get_announcement(ann_id)
    if not ann or not ann.passenger_phone:
        await callback.answer("📞 Telefon raqami ko'rsatilmagan.", show_alert=True)
        return

    await callback.answer(
        f"📞 {ann.passenger_name}\n\n{ann.passenger_phone}",
        show_alert=True
    )
