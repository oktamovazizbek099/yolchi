import re

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import F

from apps.main.models import (
    User,
    Announcement,
    BotSetting,
    BroadcastMessage,
    TelegramGroup,
    RoleChoices,
    AnnouncementStatus,
    GroupType,
)

PHONE_REGEX = re.compile(
    r'(\+?998[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2})'
    r'|(\b\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b)'
)


USERNAME_REGEX = re.compile(r'@[a-zA-Z][a-zA-Z0-9_]{4,31}')


def extract_phone(text: str):
    """Matndan telefon raqamini ajratib olish (topilmasa None)."""
    if not text:
        return None
    match = PHONE_REGEX.search(text)
    if not match:
        return None
    return match.group(0).replace(' ', '').replace('-', '')


def mask_contacts(text: str) -> str:
    """
    Ommaviy (guruh) matni uchun aloqa ma'lumotlarini berkitish.

    Yo'lovchi telefon raqamini yoki telegram userini xabar matnining ichiga
    yozib yuborishi mumkin — u holda raqam guruhdagi hamma haydovchiga
    ko'rinib qolardi. Shuning uchun ular niqoblanadi.
    """
    if not text:
        return text
    masked = PHONE_REGEX.sub("🔒[raqam yopiq]", text)
    masked = USERNAME_REGEX.sub("🔒[user yopiq]", masked)
    return masked


# ========================================
# AUTENTIFIKATSIYA
# ========================================

@sync_to_async
def authenticate_operator(telegram_id: int, password: str):
    """
    Operator parolini tekshirish. To'g'ri bo'lsa telegram_id biriktiriladi.
    """
    operator = User.objects.filter(
        role=RoleChoices.OPERATOR,
        operator_password=password.strip()
    ).first()

    if not operator:
        return None

    # Bir xil telegram_id boshqa hisobga bog'lanib qolmasligi uchun tozalash
    User.objects.filter(telegram_id=telegram_id).exclude(pk=operator.pk).update(
        telegram_id=None, is_telegram_authenticated=False
    )
    operator.telegram_id = telegram_id
    operator.is_telegram_authenticated = True
    operator.save()
    return operator


@sync_to_async
def authenticate_superadmin(telegram_id: int, password: str):
    """
    Superadmin parolini tekshirish.
    Parol BotSetting.superadmin_bot_password yoki User.operator_password bo'lishi mumkin.
    """
    password = (password or '').strip()
    if not password:
        return None

    setting, _ = BotSetting.objects.get_or_create(id=1)

    user = User.objects.filter(
        role=RoleChoices.SUPERADMIN,
        operator_password=password
    ).first()

    if not user and setting.superadmin_bot_password and setting.superadmin_bot_password == password:
        user = User.objects.filter(role=RoleChoices.SUPERADMIN).order_by('id').first()
        if not user:
            user = User.objects.filter(is_superuser=True).order_by('id').first()

    if not user:
        return None

    User.objects.filter(telegram_id=telegram_id).exclude(pk=user.pk).update(
        telegram_id=None, is_telegram_authenticated=False
    )
    user.telegram_id = telegram_id
    user.is_telegram_authenticated = True
    if user.role != RoleChoices.SUPERADMIN:
        user.role = RoleChoices.SUPERADMIN
    user.save()
    return user


@sync_to_async
def get_user_by_telegram_id(telegram_id: int):
    return User.objects.filter(telegram_id=telegram_id).first()


@sync_to_async
def is_admin_user(telegram_id: int):
    """
    Guruh buyruqlarini ishlatishga huquqi bormi?
    Superadmin yoki avtorizatsiyadan o'tgan operator.
    """
    user = User.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return None
    if user.role == RoleChoices.SUPERADMIN or user.is_superuser:
        return user
    if user.role == RoleChoices.OPERATOR and user.is_telegram_authenticated:
        return user
    return None


# ========================================
# HAYDOVCHILAR
# ========================================

@sync_to_async
def register_or_update_driver(telegram_id: int, phone_number: str, full_name: str):
    """
    Haydovchini ro'yxatga olish yoki telefonini yangilash.
    Diqqat: operator/superadmin roli o'zgartirilmaydi (faqat telefon yangilanadi).
    """
    user = User.objects.filter(telegram_id=telegram_id).first()

    if user is None:
        user = User.objects.create(
            username=f"driver_{telegram_id}",
            first_name=full_name or '',
            telegram_id=telegram_id,
            phone_number=phone_number,
            role=RoleChoices.DRIVER,
            is_driver_active=True,
            is_telegram_authenticated=True,
        )
        return user, True

    user.phone_number = phone_number
    if user.role in (RoleChoices.SUPERADMIN, RoleChoices.OPERATOR):
        # Rolni saqlab qolamiz — faqat telefon yangilandi
        user.save()
        return user, False

    user.first_name = full_name or user.first_name
    user.role = RoleChoices.DRIVER
    user.is_driver_active = True
    user.is_telegram_authenticated = True
    user.save()
    return user, False


@sync_to_async
def get_active_drivers():
    return list(User.objects.filter(
        role=RoleChoices.DRIVER,
        is_driver_active=True,
        is_active=True,
        telegram_id__isnull=False
    ))


# ========================================
# GURUHLAR
# ========================================

@sync_to_async
def register_group(chat_id: int, title: str, group_type: str, added_by=None):
    """
    Guruhni ro'yxatga olish yoki turini yangilash.
    Returns: (group, created, old_type)
    """
    group = TelegramGroup.objects.filter(chat_id=chat_id).first()

    if group is None:
        group = TelegramGroup.objects.create(
            chat_id=chat_id,
            title=title or '',
            group_type=group_type,
            is_active=True,
            added_by=added_by,
        )
        return group, True, None

    old_type = group.group_type
    group.title = title or group.title
    group.group_type = group_type
    group.is_active = True
    if added_by:
        group.added_by = added_by
    group.save()
    return group, False, old_type


@sync_to_async
def unregister_group(chat_id: int):
    deleted, _ = TelegramGroup.objects.filter(chat_id=chat_id).delete()
    return deleted > 0


@sync_to_async
def get_group(chat_id: int):
    return TelegramGroup.objects.filter(chat_id=chat_id).first()


@sync_to_async
def get_source_group(chat_id: int):
    """
    Xabar keladigan guruh ro'yxatda va aktiv PASSENGER turidami?
    Aks holda None -> xabar butunlay e'tiborsiz qoldiriladi.
    """
    return TelegramGroup.objects.filter(
        chat_id=chat_id,
        group_type=GroupType.PASSENGER,
        is_active=True
    ).first()


@sync_to_async
def get_driver_groups():
    return list(TelegramGroup.objects.filter(
        group_type=GroupType.DRIVER,
        is_active=True
    ))


@sync_to_async
def get_all_groups(group_type=None):
    qs = TelegramGroup.objects.all()
    if group_type:
        qs = qs.filter(group_type=group_type)
    return list(qs)


@sync_to_async
def toggle_group_active(group_id: int):
    group = TelegramGroup.objects.filter(id=group_id).first()
    if not group:
        return None
    group.is_active = not group.is_active
    group.save()
    return group


@sync_to_async
def delete_group_by_id(group_id: int):
    group = TelegramGroup.objects.filter(id=group_id).first()
    if not group:
        return None
    title = group.title or str(group.chat_id)
    group.delete()
    return title


# ========================================
# BUYURTMALAR
# ========================================

def build_order_text(order_number, passenger_name, phone, username, source_group_name, raw_text):
    """
    HAYDOVCHILAR GURUHIGA yuboriladigan OMMAVIY matn.
    Yo'lovchining telefoni va useri BU YERDA KO'RSATILMAYDI — ular faqat
    buyurtmani birinchi bo'lib olgan haydovchiga shaxsiy yuboriladi.
    """
    line = '━' * 20
    text = f"🚕 {order_number}-BUYURTMA\n{line}\n\n"
    text += f"🧑 Mijoz: {passenger_name}\n"

    if source_group_name:
        text += f"📍 Guruh: {source_group_name}\n"

    # Yo'lovchi raqamini matn ichiga yozgan bo'lishi mumkin — niqoblaymiz
    text += f"\n📋 Buyurtma:\n{mask_contacts(raw_text)}\n"
    text += f"{line}\n"
    text += "🔒 Aloqa ma'lumotlari buyurtmani olgan haydovchiga yuboriladi.\n\n"
    text += "🔴 BUYURTMANI QO'LGA KIRITISH UCHUN TEZROQ HARAKAT QILING!!!"
    return text


def build_private_order_text(ann):
    """
    Buyurtmani olgan haydovchiga SHAXSIY yuboriladigan to'liq matn —
    yo'lovchining telefoni va telegram useri shu yerda.
    """
    line = '━' * 20
    text = f"✅ #{ann.id} — buyurtma sizniki!\n{line}\n\n"
    text += f"🧑 Mijoz: {ann.passenger_name}\n"

    if ann.passenger_phone:
        text += f"📞 Aloqa: {ann.passenger_phone}\n"
    if ann.passenger_username:
        text += f"💬 Telegram: @{ann.passenger_username}\n"
    if not ann.passenger_phone and not ann.passenger_username:
        text += "📞 Aloqa: raqam ko'rsatilmagan — profil orqali yozing\n"

    if ann.source_group_name:
        text += f"📍 Guruh: {ann.source_group_name}\n"

    text += f"\n📋 Buyurtma:\n{ann.raw_text}\n"
    text += f"{line}\n"
    text += "Pastdagi tugmalar orqali bog'laning."
    return text


@sync_to_async
def create_announcement_from_group(passenger_name, passenger_tg_id, passenger_username,
                                   raw_text, group_msg_id, source_group_id=None,
                                   source_group_name=None):
    """Guruhdan kelgan xabarni buyurtma sifatida saqlash (tartib raqami atomik oshiriladi)."""
    with transaction.atomic():
        BotSetting.objects.get_or_create(id=1)
        # F() ifodasi bilan poyga shartisiz oshirish
        BotSetting.objects.filter(id=1).update(order_counter=F('order_counter') + 1)
        order_number = BotSetting.objects.values_list('order_counter', flat=True).get(id=1)

        phone = extract_phone(raw_text)
        formatted = build_order_text(
            order_number=order_number,
            passenger_name=passenger_name,
            phone=phone,
            username=passenger_username,
            source_group_name=source_group_name,
            raw_text=raw_text,
        )

        announcement = Announcement.objects.create(
            passenger_name=passenger_name,
            passenger_telegram_id=passenger_tg_id,
            passenger_username=passenger_username,
            passenger_phone=phone,
            raw_text=raw_text,
            formatted_text=formatted,
            group_message_id=group_msg_id,
            source_group_id=source_group_id,
            source_group_name=source_group_name,
            status=AnnouncementStatus.NEW,
        )
    return announcement


@sync_to_async
def get_pending_announcements(limit=10):
    return list(
        Announcement.objects.filter(status=AnnouncementStatus.NEW)
        .order_by('-created_at')[:limit]
    )


@sync_to_async
def get_announcement(announcement_id: int):
    return Announcement.objects.filter(id=announcement_id).first()


@sync_to_async
def mark_announcement_broadcasted(announcement_id, operator_user=None):
    ann = Announcement.objects.filter(id=announcement_id).first()
    if not ann:
        return None
    # ACCEPTED holatini orqaga qaytarib yubormaymiz
    if ann.status == AnnouncementStatus.NEW:
        ann.status = AnnouncementStatus.BROADCASTED
    if operator_user:
        ann.created_by_operator = operator_user
    ann.save()
    return ann


@sync_to_async
def save_broadcast_message(announcement_id: int, chat_id: int, message_id: int, is_group=True):
    """Yuborilgan har bir nusxaning ID sini saqlash (keyin tahrirlash uchun)."""
    BroadcastMessage.objects.get_or_create(
        announcement_id=announcement_id,
        chat_id=chat_id,
        message_id=message_id,
        defaults={'is_group': is_group},
    )


@sync_to_async
def get_broadcast_messages(announcement_id: int):
    return list(BroadcastMessage.objects.filter(announcement_id=announcement_id))


@sync_to_async
def accept_order(announcement_id: int, driver_telegram_id: int):
    """
    Buyurtmani qabul qilish — atomik, poyga shartisiz.
    Returns: (announcement, driver, already_taken_by)
      - (None, None, None)         -> buyurtma topilmadi
      - (ann, None, driver)        -> allaqachon boshqa haydovchi olgan
      - (ann, None, None)          -> bosgan odam haydovchi emas
      - (ann, driver, None)        -> muvaffaqiyatli
    """
    from django.utils import timezone

    with transaction.atomic():
        ann = (
            Announcement.objects
            .select_for_update()
            .filter(id=announcement_id)
            .first()
        )
        if ann is None:
            return None, None, None

        if ann.accepted_by_driver_id:
            taken_by = User.objects.filter(id=ann.accepted_by_driver_id).first()
            return ann, None, taken_by

        driver = User.objects.filter(
            telegram_id=driver_telegram_id,
            role=RoleChoices.DRIVER,
            is_active=True,
        ).first()
        if driver is None:
            return ann, None, None

        ann.accepted_by_driver = driver
        ann.accepted_at = timezone.now()
        ann.status = AnnouncementStatus.ACCEPTED
        ann.save()

    return ann, driver, None


@sync_to_async
def get_driver_orders(driver_telegram_id: int, limit=5):
    """Haydovchi qabul qilgan oxirgi buyurtmalar."""
    return list(
        Announcement.objects
        .filter(accepted_by_driver__telegram_id=driver_telegram_id)
        .order_by('-accepted_at')[:limit]
    )


@sync_to_async
def get_accepted_driver_tg_id(announcement_id: int):
    """
    Buyurtmani qabul qilgan haydovchining telegram_id si.
    Aloqa ma'lumotlarini ko'rsatishdan oldin shu bilan tekshiriladi.
    """
    return (
        Announcement.objects
        .filter(id=announcement_id)
        .values_list('accepted_by_driver__telegram_id', flat=True)
        .first()
    )


@sync_to_async
def cancel_order(announcement_id: int):
    """Buyurtmani bekor qilish (superadmin uchun)."""
    ann = Announcement.objects.filter(id=announcement_id).first()
    if not ann:
        return None
    ann.status = AnnouncementStatus.CANCELLED
    ann.save()
    return ann


# ========================================
# SOZLAMALAR
# ========================================

@sync_to_async
def get_bot_settings():
    setting, _ = BotSetting.objects.get_or_create(id=1)
    return setting


@sync_to_async
def toggle_auto_broadcast():
    setting, _ = BotSetting.objects.get_or_create(id=1)
    setting.auto_broadcast = not setting.auto_broadcast
    setting.save()
    return setting


@sync_to_async
def toggle_smart_filter():
    setting, _ = BotSetting.objects.get_or_create(id=1)
    setting.smart_filter = not setting.smart_filter
    setting.save()
    return setting


# ========================================
# SUPERADMIN FUNKSIYALARI
# ========================================

@sync_to_async
def get_all_users(role_filter=None, limit=None):
    qs = User.objects.all().order_by('role', 'id')
    if role_filter:
        qs = qs.filter(role=role_filter)
    if limit:
        qs = qs[:limit]
    return list(qs)


@sync_to_async
def delete_user_by_id(user_id: int):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return None
    name = user.get_full_name() or user.username
    user.delete()
    return name


@sync_to_async
def toggle_user_active(user_id: int):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return None
    user.is_active = not user.is_active
    user.save()
    return user


@sync_to_async
def get_user_by_id(user_id: int):
    return User.objects.filter(id=user_id).first()


@sync_to_async
def get_statistics():
    stats = {
        'total_users': User.objects.count(),
        'drivers_count': User.objects.filter(role=RoleChoices.DRIVER).count(),
        'active_drivers': User.objects.filter(
            role=RoleChoices.DRIVER, is_driver_active=True, is_active=True
        ).count(),
        'operators_count': User.objects.filter(role=RoleChoices.OPERATOR).count(),
        'total_orders': Announcement.objects.count(),
        'new_orders': Announcement.objects.filter(status=AnnouncementStatus.NEW).count(),
        'accepted_orders': Announcement.objects.filter(status=AnnouncementStatus.ACCEPTED).count(),
        'broadcasted_orders': Announcement.objects.filter(status=AnnouncementStatus.BROADCASTED).count(),
        'passenger_groups': TelegramGroup.objects.filter(
            group_type=GroupType.PASSENGER, is_active=True
        ).count(),
        'driver_groups': TelegramGroup.objects.filter(
            group_type=GroupType.DRIVER, is_active=True
        ).count(),
    }
    return stats
