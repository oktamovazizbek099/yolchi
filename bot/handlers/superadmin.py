"""
Telegram bot ichidagi superadmin paneli.

Kirish:  /admin  ->  parol  ->  panel
Panel:   guruhlar, haydovchilar, operatorlar, statistika, sozlamalar
"""
import logging

from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from apps.main.models import GroupType, RoleChoices
from bot.utils.db_api import (
    authenticate_superadmin,
    delete_group_by_id,
    delete_user_by_id,
    get_all_groups,
    get_all_users,
    get_bot_settings,
    get_statistics,
    get_user_by_id,
    get_user_by_telegram_id,
    toggle_auto_broadcast,
    toggle_group_active,
    toggle_smart_filter,
    toggle_user_active,
)

logger = logging.getLogger(__name__)

# Kirish routeri — /admin va parol. Hamma uchun ochiq.
router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)


class AdminStates(StatesGroup):
    waiting_for_password = State()


BTN_GROUPS = "👥 Guruhlar"
BTN_DRIVERS = "🚗 Haydovchilar"
BTN_OPERATORS = "🎧 Operatorlar"
BTN_STATS = "📊 Statistika"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_EXIT = "🚪 Paneldan chiqish"


def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_GROUPS), KeyboardButton(text=BTN_DRIVERS)],
            [KeyboardButton(text=BTN_OPERATORS), KeyboardButton(text=BTN_STATS)],
            [KeyboardButton(text=BTN_SETTINGS), KeyboardButton(text=BTN_EXIT)],
        ],
        resize_keyboard=True,
    )


async def require_superadmin(telegram_id: int):
    user = await get_user_by_telegram_id(telegram_id)
    if user and (user.role == RoleChoices.SUPERADMIN or user.is_superuser) \
            and user.is_telegram_authenticated:
        return user
    return None


class IsSuperAdmin(BaseFilter):
    """
    Panel routeri uchun filtr. Superadmin bo'lmagan foydalanuvchining xabari
    bu routerga umuman tushmaydi va operator/haydovchi handleriga o'tib ketadi
    (masalan '🚗 Haydovchilar' tugmasi ikkala panelda ham bor).
    """
    async def __call__(self, event) -> bool:
        user = getattr(event, 'from_user', None)
        if user is None:
            return False
        return await require_superadmin(user.id) is not None


# Panel routeri — faqat avtorizatsiyadan o'tgan superadmin uchun.
panel_router = Router()
panel_router.message.filter(F.chat.type == ChatType.PRIVATE, IsSuperAdmin())
panel_router.callback_query.filter(IsSuperAdmin())


# ========================================
# KIRISH
# ========================================

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    user = await require_superadmin(message.from_user.id)
    if user:
        await state.clear()
        await message.answer(
            f"👑 Superadmin paneli\n\nXush kelibsiz, {user.get_full_name() or user.username}!",
            reply_markup=admin_keyboard(),
            parse_mode=None,
        )
        return

    await state.set_state(AdminStates.waiting_for_password)
    await message.answer(
        "🔐 Superadmin parolini kiriting:\n\n"
        "(Bekor qilish uchun /start bosing)",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=None,
    )


@router.message(AdminStates.waiting_for_password, F.text, ~F.text.startswith('/'))
async def process_admin_password(message: Message, state: FSMContext):
    user = await authenticate_superadmin(message.from_user.id, message.text or '')

    if not user:
        await message.answer(
            "❌ Parol xato. Qayta urinib ko'ring yoki /start bosing.",
            parse_mode=None,
        )
        return

    await state.clear()
    await message.answer(
        f"✅ Superadmin sifatida kirdingiz!\n\n{user.get_full_name() or user.username}",
        reply_markup=admin_keyboard(),
        parse_mode=None,
    )


@panel_router.message(F.text == BTN_EXIT)
async def admin_exit(message: Message, state: FSMContext):
    user = await require_superadmin(message.from_user.id)
    if not user:
        return

    from asgiref.sync import sync_to_async
    user.is_telegram_authenticated = False
    await sync_to_async(user.save)()

    await state.clear()
    from bot.handlers.start import get_main_keyboard
    await message.answer(
        "🚪 Paneldan chiqdingiz.",
        reply_markup=get_main_keyboard(None),
        parse_mode=None,
    )


# ========================================
# GURUHLAR
# ========================================

def groups_keyboard(groups):
    rows = []
    for g in groups:
        icon = "📥" if g.group_type == GroupType.PASSENGER else "📤"
        state_icon = "🟢" if g.is_active else "🔴"
        name = (g.title or str(g.chat_id))[:22]
        rows.append([
            InlineKeyboardButton(
                text=f"{icon}{state_icon} {name}",
                callback_data=f"grp_info_{g.id}"
            ),
            InlineKeyboardButton(
                text="⏻" if g.is_active else "▶️",
                callback_data=f"grp_toggle_{g.id}"
            ),
            InlineKeyboardButton(text="🗑", callback_data=f"grp_del_{g.id}"),
        ])
    rows.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="grp_refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def groups_text(groups):
    passengers = [g for g in groups if g.group_type == GroupType.PASSENGER]
    drivers = [g for g in groups if g.group_type == GroupType.DRIVER]

    text = "👥 Ro'yxatdagi guruhlar\n\n"
    text += f"📥 Yo'lovchilar guruhlari: {len(passengers)} ta\n"
    text += f"📤 Haydovchilar guruhlari: {len(drivers)} ta\n\n"

    if not groups:
        text += (
            "Hali birorta guruh qo'shilmagan.\n\n"
            "Qo'shish uchun botni guruhga qo'shing va o'sha guruhda yozing:\n"
            "  /yolovchi_guruh — buyurtmalar shu yerdan olinadi\n"
            "  /haydovchi_guruh — buyurtmalar shu yerga yuboriladi"
        )
        return text

    if not drivers:
        text += "⚠️ Haydovchilar guruhi yo'q — buyurtmalar hech kimga bormaydi!\n\n"
    if not passengers:
        text += "⚠️ Yo'lovchilar guruhi yo'q — bot hech qayerdan buyurtma olmaydi!\n\n"

    text += "🟢 aktiv  🔴 o'chirilgan  |  ⏻ o'chirish  🗑 ro'yxatdan olib tashlash"
    return text


@panel_router.message(F.text == BTN_GROUPS)
async def show_groups(message: Message):
    if not await require_superadmin(message.from_user.id):
        return
    groups = await get_all_groups()
    await message.answer(groups_text(groups), reply_markup=groups_keyboard(groups), parse_mode=None)


@panel_router.callback_query(F.data == "grp_refresh")
async def cb_groups_refresh(callback: CallbackQuery):
    if not await require_superadmin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return
    groups = await get_all_groups()
    try:
        await callback.message.edit_text(
            groups_text(groups), reply_markup=groups_keyboard(groups), parse_mode=None
        )
    except Exception:
        pass
    await callback.answer("🔄 Yangilandi")


@panel_router.callback_query(F.data.startswith("grp_info_"))
async def cb_group_info(callback: CallbackQuery):
    if not await require_superadmin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return

    group_id = int(callback.data.rsplit("_", 1)[1])
    groups = await get_all_groups()
    group = next((g for g in groups if g.id == group_id), None)

    if not group:
        await callback.answer("Guruh topilmadi", show_alert=True)
        return

    turi = "Yo'lovchilar (bot o'qiydi)" if group.group_type == GroupType.PASSENGER \
        else "Haydovchilar (bot yozadi)"
    await callback.answer(
        f"{group.title or 'Nomsiz'}\n\n"
        f"ID: {group.chat_id}\n"
        f"Turi: {turi}\n"
        f"Holat: {'Aktiv' if group.is_active else 'O`chirilgan'}",
        show_alert=True,
    )


@panel_router.callback_query(F.data.startswith("grp_toggle_"))
async def cb_group_toggle(callback: CallbackQuery):
    if not await require_superadmin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return

    group_id = int(callback.data.rsplit("_", 1)[1])
    group = await toggle_group_active(group_id)
    if not group:
        await callback.answer("Guruh topilmadi", show_alert=True)
        return

    groups = await get_all_groups()
    try:
        await callback.message.edit_text(
            groups_text(groups), reply_markup=groups_keyboard(groups), parse_mode=None
        )
    except Exception:
        pass
    await callback.answer("🟢 Aktivlashtirildi" if group.is_active else "🔴 O'chirildi")


@panel_router.callback_query(F.data.startswith("grp_del_"))
async def cb_group_delete(callback: CallbackQuery):
    if not await require_superadmin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return

    group_id = int(callback.data.rsplit("_", 1)[1])
    title = await delete_group_by_id(group_id)

    groups = await get_all_groups()
    try:
        await callback.message.edit_text(
            groups_text(groups), reply_markup=groups_keyboard(groups), parse_mode=None
        )
    except Exception:
        pass
    await callback.answer(f"🗑 O'chirildi: {title}" if title else "Topilmadi")


# ========================================
# HAYDOVCHILAR / OPERATORLAR
# ========================================

def users_keyboard(users, prefix):
    rows = []
    for u in users[:20]:
        state_icon = "🟢" if u.is_active else "⛔️"
        name = (u.first_name or u.username or str(u.telegram_id))[:20]
        rows.append([
            InlineKeyboardButton(text=f"{state_icon} {name}", callback_data=f"usr_info_{u.id}"),
            InlineKeyboardButton(text="⛔️" if u.is_active else "✅",
                                 callback_data=f"usr_toggle_{u.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"usr_del_{u.id}"),
        ])
    rows.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"usr_refresh_{prefix}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def drivers_text(drivers):
    active = sum(1 for d in drivers if d.is_driver_active and d.is_active)
    text = f"🚗 Haydovchilar: {len(drivers)} ta (aktiv: {active})\n\n"
    if not drivers:
        return text + "Hali birorta haydovchi ro'yxatdan o'tmagan."
    for d in drivers[:20]:
        status = "🟢" if (d.is_driver_active and d.is_active) else "⛔️"
        text += f"{status} {d.first_name or d.username} — {d.phone_number or 'tel yo`q'}\n"
    if len(drivers) > 20:
        text += f"\n... va yana {len(drivers) - 20} ta"
    return text


def operators_text(operators):
    text = f"🎧 Operatorlar: {len(operators)} ta\n\n"
    if not operators:
        return text + "Operator yo'q. Django admin panelidan qo'shishingiz mumkin."
    for o in operators[:20]:
        auth = "🟢 botda" if o.is_telegram_authenticated else "⚪️ botga kirmagan"
        text += f"• {o.get_full_name() or o.username} — {auth}\n"
    return text


@panel_router.message(F.text == BTN_DRIVERS)
async def show_drivers(message: Message):
    if not await require_superadmin(message.from_user.id):
        return
    drivers = await get_all_users(role_filter=RoleChoices.DRIVER)
    await message.answer(
        drivers_text(drivers), reply_markup=users_keyboard(drivers, "drv"), parse_mode=None
    )


@panel_router.message(F.text == BTN_OPERATORS)
async def show_operators(message: Message):
    if not await require_superadmin(message.from_user.id):
        return
    operators = await get_all_users(role_filter=RoleChoices.OPERATOR)
    await message.answer(
        operators_text(operators), reply_markup=users_keyboard(operators, "opr"), parse_mode=None
    )


async def _refresh_users(callback: CallbackQuery, prefix: str):
    if prefix == "drv":
        users = await get_all_users(role_filter=RoleChoices.DRIVER)
        text = drivers_text(users)
    else:
        users = await get_all_users(role_filter=RoleChoices.OPERATOR)
        text = operators_text(users)
    try:
        await callback.message.edit_text(
            text, reply_markup=users_keyboard(users, prefix), parse_mode=None
        )
    except Exception:
        pass


@panel_router.callback_query(F.data.startswith("usr_refresh_"))
async def cb_users_refresh(callback: CallbackQuery):
    if not await require_superadmin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return
    await _refresh_users(callback, callback.data.rsplit("_", 1)[1])
    await callback.answer("🔄 Yangilandi")


@panel_router.callback_query(F.data.startswith("usr_info_"))
async def cb_user_info(callback: CallbackQuery):
    if not await require_superadmin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return

    user = await get_user_by_id(int(callback.data.rsplit("_", 1)[1]))
    if not user:
        await callback.answer("Topilmadi", show_alert=True)
        return

    await callback.answer(
        f"{user.get_full_name() or user.username}\n\n"
        f"Rol: {user.get_role_display()}\n"
        f"Tel: {user.phone_number or '—'}\n"
        f"TG ID: {user.telegram_id or '—'}\n"
        f"Holat: {'Aktiv' if user.is_active else 'Bloklangan'}",
        show_alert=True,
    )


@panel_router.callback_query(F.data.startswith("usr_toggle_"))
async def cb_user_toggle(callback: CallbackQuery):
    if not await require_superadmin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return

    user = await toggle_user_active(int(callback.data.rsplit("_", 1)[1]))
    if not user:
        await callback.answer("Topilmadi", show_alert=True)
        return

    prefix = "drv" if user.role == RoleChoices.DRIVER else "opr"
    await _refresh_users(callback, prefix)
    await callback.answer("✅ Aktivlashtirildi" if user.is_active else "⛔️ Bloklandi")


@panel_router.callback_query(F.data.startswith("usr_del_"))
async def cb_user_delete(callback: CallbackQuery):
    admin = await require_superadmin(callback.from_user.id)
    if not admin:
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return

    user_id = int(callback.data.rsplit("_", 1)[1])
    if user_id == admin.id:
        await callback.answer("❌ O'zingizni o'chira olmaysiz!", show_alert=True)
        return

    target = await get_user_by_id(user_id)
    prefix = "drv" if (target and target.role == RoleChoices.DRIVER) else "opr"

    name = await delete_user_by_id(user_id)
    await _refresh_users(callback, prefix)
    await callback.answer(f"🗑 O'chirildi: {name}" if name else "Topilmadi")


# ========================================
# STATISTIKA VA SOZLAMALAR
# ========================================

@panel_router.message(F.text == BTN_STATS)
async def show_stats(message: Message):
    if not await require_superadmin(message.from_user.id):
        return

    s = await get_statistics()
    await message.answer(
        "📊 Umumiy statistika\n"
        f"{'─' * 22}\n\n"
        f"👥 Foydalanuvchilar: {s['total_users']}\n"
        f"🚗 Haydovchilar: {s['drivers_count']} (bo'sh: {s['active_drivers']})\n"
        f"🎧 Operatorlar: {s['operators_count']}\n\n"
        f"📥 Yo'lovchi guruhlari: {s['passenger_groups']}\n"
        f"📤 Haydovchi guruhlari: {s['driver_groups']}\n\n"
        f"📋 Jami buyurtmalar: {s['total_orders']}\n"
        f"🆕 Kutilmoqda: {s['new_orders']}\n"
        f"📢 Yuborilgan: {s['broadcasted_orders']}\n"
        f"✅ Qabul qilingan: {s['accepted_orders']}\n",
        parse_mode=None,
    )


def settings_keyboard(setting):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'🟢' if setting.auto_broadcast else '🔴'} Shaxsiy xabar yuborish",
            callback_data="set_autobroadcast"
        )],
        [InlineKeyboardButton(
            text=f"{'🟢' if setting.smart_filter else '🔴'} Aqlli filtr",
            callback_data="set_smartfilter"
        )],
    ])


def settings_text(setting):
    return (
        "⚙️ Bot sozlamalari\n"
        f"{'─' * 22}\n\n"
        f"📢 Shaxsiy xabar: {'yoqilgan' if setting.auto_broadcast else 'o`chirilgan'}\n"
        "   Buyurtma haydovchilar guruhidan tashqari har bir haydovchiga\n"
        "   shaxsiy ham yuboriladi.\n\n"
        f"🧠 Aqlli filtr: {'yoqilgan' if setting.smart_filter else 'o`chirilgan'}\n"
        f"   Minimal uzunlik: {setting.min_order_length} belgi\n"
        "   'salom', 'rahmat', emoji kabi xabarlar buyurtma deb hisoblanmaydi.\n\n"
        f"🔢 Oxirgi buyurtma raqami: {setting.order_counter}"
    )


@panel_router.message(F.text == BTN_SETTINGS)
async def show_settings(message: Message):
    if not await require_superadmin(message.from_user.id):
        return
    setting = await get_bot_settings()
    await message.answer(
        settings_text(setting), reply_markup=settings_keyboard(setting), parse_mode=None
    )


@panel_router.callback_query(F.data == "set_autobroadcast")
async def cb_toggle_autobroadcast(callback: CallbackQuery):
    if not await require_superadmin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return
    setting = await toggle_auto_broadcast()
    try:
        await callback.message.edit_text(
            settings_text(setting), reply_markup=settings_keyboard(setting), parse_mode=None
        )
    except Exception:
        pass
    await callback.answer("🟢 Yoqildi" if setting.auto_broadcast else "🔴 O'chirildi")


@panel_router.callback_query(F.data == "set_smartfilter")
async def cb_toggle_smartfilter(callback: CallbackQuery):
    if not await require_superadmin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return
    setting = await toggle_smart_filter()
    try:
        await callback.message.edit_text(
            settings_text(setting), reply_markup=settings_keyboard(setting), parse_mode=None
        )
    except Exception:
        pass
    await callback.answer("🟢 Yoqildi" if setting.smart_filter else "🔴 O'chirildi")
