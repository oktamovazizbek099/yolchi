from asgiref.sync import sync_to_async
from apps.main.models import User, Announcement, BotSetting, RoleChoices, AnnouncementStatus

@sync_to_async
def authenticate_operator(telegram_id: int, password: str):
    """
    Operator matching logic:
    Checks if there is a User with role=OPERATOR whose operator_password matches.
    If matched, links their telegram_id and sets is_telegram_authenticated=True.
    """
    operator = User.objects.filter(
        role=RoleChoices.OPERATOR,
        operator_password=password.strip()
    ).first()
    
    if operator:
        operator.telegram_id = telegram_id
        operator.is_telegram_authenticated = True
        operator.save()
        return operator
    return None

@sync_to_async
def get_user_by_telegram_id(telegram_id: int):
    return User.objects.filter(telegram_id=telegram_id).first()

@sync_to_async
def register_or_update_driver(telegram_id: int, phone_number: str, full_name: str):
    driver, created = User.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={
            'username': f"driver_{telegram_id}",
            'first_name': full_name,
            'phone_number': phone_number,
            'role': RoleChoices.DRIVER,
            'is_driver_active': True,
            'is_telegram_authenticated': True
        }
    )
    if not created:
        driver.phone_number = phone_number
        driver.first_name = full_name
        driver.role = RoleChoices.DRIVER
        driver.is_driver_active = True
        driver.is_telegram_authenticated = True
        driver.save()
    return driver

@sync_to_async
def get_active_drivers():
    return list(User.objects.filter(role=RoleChoices.DRIVER, is_driver_active=True, telegram_id__isnull=False))

@sync_to_async
def create_announcement_from_group(passenger_name, passenger_tg_id, passenger_username, raw_text, group_msg_id):
    # Basic keyword parsing logic for location & time
    from_loc = "Noma'lum"
    to_loc = "Noma'lum"
    
    formatted = f"📢 **YANGI BUYURTMA (YO'LOVCHI)**\n\n"
    formatted += f"👤 **Yo'lovchi:** {passenger_name}\n"
    if passenger_username:
        formatted += f"💬 **Telegram:** @{passenger_username}\n"
    formatted += f"📝 **Matn:** {raw_text}\n"
    
    announcement = Announcement.objects.create(
        passenger_name=passenger_name,
        passenger_telegram_id=passenger_tg_id,
        passenger_username=passenger_username,
        raw_text=raw_text,
        formatted_text=formatted,
        from_location=from_loc,
        to_location=to_loc,
        group_message_id=group_msg_id,
        status=AnnouncementStatus.NEW
    )
    return announcement

@sync_to_async
def get_pending_announcements():
    return list(Announcement.objects.filter(status=AnnouncementStatus.NEW).order_by('-created_at')[:10])

@sync_to_async
def mark_announcement_broadcasted(announcement_id, operator_user=None):
    try:
        ann = Announcement.objects.get(id=announcement_id)
        ann.status = AnnouncementStatus.BROADCASTED
        if operator_user:
            ann.created_by_operator = operator_user
        ann.save()
        return ann
    except Announcement.DoesNotExist:
        return None

@sync_to_async
def get_bot_settings():
    setting, _ = BotSetting.objects.get_or_create(id=1)
    return setting
