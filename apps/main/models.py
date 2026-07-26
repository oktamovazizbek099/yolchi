from django.db import models
from django.contrib.auth.models import AbstractUser

class RoleChoices(models.TextChoices):
    SUPERADMIN = 'SUPERADMIN', 'Superadmin (Web Admin)'
    OPERATOR = 'OPERATOR', 'Operator (Telegram Operator)'
    DRIVER = 'DRIVER', 'Haydovchi'
    PASSENGER = 'PASSENGER', 'Yo\'lovchi'

class User(AbstractUser):
    role = models.CharField(
        max_length=20, 
        choices=RoleChoices.choices, 
        default=RoleChoices.DRIVER,
        verbose_name="Foydalanuvchi Roli"
    )
    telegram_id = models.BigIntegerField(
        unique=True, 
        null=True, 
        blank=True, 
        verbose_name="Telegram ID"
    )
    phone_number = models.CharField(
        max_length=30, 
        blank=True, 
        null=True, 
        verbose_name="Telefon Raqami"
    )
    operator_password = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Operator Telegram Bot Paroli",
        help_text="Web admin tomonidan Telegram botga kirish uchun beriladigan parol"
    )
    is_driver_active = models.BooleanField(
        default=True, 
        verbose_name="Haydovchi Holati (Aktiv)"
    )
    is_telegram_authenticated = models.BooleanField(
        default=False, 
        verbose_name="Botda Avtorizatsiyadan o'tgan"
    )

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    def __str__(self):
        name = self.get_full_name() or self.username
        return f"{name} ({self.get_role_display()})"


class GroupType(models.TextChoices):
    PASSENGER = 'PASSENGER', "Yo'lovchilar Guruhi (manba)"
    DRIVER = 'DRIVER', "Haydovchilar Guruhi (tarqatish)"


class TelegramGroup(models.Model):
    """
    Bot ishlaydigan guruhlar ro'yxati.
    PASSENGER - bot bu guruhdan xabar o'qiydi va buyurtma yasaydi.
    DRIVER    - bot bu guruhga tayyor buyurtmani tashlaydi (o'qimaydi).
    """
    chat_id = models.BigIntegerField(
        unique=True,
        verbose_name="Guruh Telegram ID",
        help_text="Masalan: -1001234567890"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Guruh Nomi"
    )
    group_type = models.CharField(
        max_length=20,
        choices=GroupType.choices,
        verbose_name="Guruh Turi"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktiv",
        help_text="O'chirilsa bot bu guruhni butunlay e'tiborsiz qoldiradi"
    )
    added_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_groups',
        verbose_name="Kim qo'shgan"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Telegram Guruh"
        verbose_name_plural = "Telegram Guruhlar"
        ordering = ['group_type', '-created_at']

    def __str__(self):
        return f"{self.title or self.chat_id} ({self.get_group_type_display()})"


class AnnouncementStatus(models.TextChoices):
    NEW = 'NEW', 'Yangi (Kutilmoqda)'
    BROADCASTED = 'BROADCASTED', 'Haydovchilarga Yuborildi'
    ACCEPTED = 'ACCEPTED', 'Haydovchi Qabul Qildi'
    CANCELLED = 'CANCELLED', 'Bekor Qilindi'


class Announcement(models.Model):
    passenger_name = models.CharField(
        max_length=255, 
        verbose_name="Yo'lovchi Ismi / Username"
    )
    passenger_telegram_id = models.BigIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Yo'lovchi Telegram ID"
    )
    passenger_username = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Yo'lovchi Telegram Usernami"
    )
    passenger_phone = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        verbose_name="Yo'lovchi Telefon Raqami"
    )
    raw_text = models.TextField(
        verbose_name="Asl Xabar Matni (Guruhdan)"
    )
    formatted_text = models.TextField(
        verbose_name="Formatlangan E'lon Matni"
    )
    from_location = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Qayerdan"
    )
    to_location = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Qayerga"
    )
    departure_time = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Jo'nash Vaqti"
    )
    status = models.CharField(
        max_length=20, 
        choices=AnnouncementStatus.choices, 
        default=AnnouncementStatus.NEW,
        verbose_name="Holati"
    )
    created_by_operator = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='processed_announcements',
        verbose_name="Tasdiqlagan Operator"
    )
    group_message_id = models.BigIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Guruh Xabar ID"
    )
    drivers_group_message_id = models.BigIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Haydovchilar Guruhi Xabar ID"
    )
    accepted_by_driver = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='accepted_orders',
        verbose_name="Qabul Qilgan Haydovchi"
    )
    accepted_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Qabul Qilingan Vaqt"
    )
    source_group_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Manba Guruh ID"
    )
    source_group_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Manba Guruh Nomi"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Yaratilgan Vaqti"
    )

    class Meta:
        verbose_name = "E'lon / Buyurtma"
        verbose_name_plural = "E'lonlar / Buyurtmalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"E'lon #{self.id} - {self.passenger_name} ({self.get_status_display()})"


class BroadcastMessage(models.Model):
    """
    Bitta buyurtma bir nechta haydovchilar guruhiga / haydovchiga yuborilishi mumkin.
    Buyurtma qabul qilinganda barcha nusxalarni tahrirlash uchun ularning ID si saqlanadi.
    """
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='broadcasts',
        verbose_name="Buyurtma"
    )
    chat_id = models.BigIntegerField(verbose_name="Chat ID")
    message_id = models.BigIntegerField(verbose_name="Xabar ID")
    is_group = models.BooleanField(default=True, verbose_name="Guruhga yuborilgan")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Yuborilgan Xabar"
        verbose_name_plural = "Yuborilgan Xabarlar"
        unique_together = ('announcement', 'chat_id', 'message_id')

    def __str__(self):
        return f"#{self.announcement_id} -> {self.chat_id}"


class BotSetting(models.Model):
    target_group_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="[Eskirgan] Kuzatiladigan Guruh Telegram ID",
        help_text="Eskirgan — endi 'Telegram Guruhlar' bo'limidan foydalaning"
    )
    auto_broadcast = models.BooleanField(
        default=False, 
        verbose_name="Avtomatik Haydovchilarga Yuborish",
        help_text="Belgilansa, guruhga tushgan e'lon operator tasdig'isiz birdaniga barcha haydovchilarga yuboriladi"
    )
    drivers_group_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="[Eskirgan] Haydovchilar Guruhi Telegram ID",
        help_text="Eskirgan — endi 'Telegram Guruhlar' bo'limidan foydalaning"
    )
    min_order_length = models.PositiveIntegerField(
        default=10,
        verbose_name="Minimal Xabar Uzunligi",
        help_text="Shundan qisqa xabarlar buyurtma deb hisoblanmaydi (aqlli filtr)"
    )
    smart_filter = models.BooleanField(
        default=True,
        verbose_name="Aqlli Filtr Yoqilgan",
        help_text="Salomlashish, emoji va juda qisqa xabarlarni o'tkazib yuborish"
    )
    superadmin_bot_password = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Superadmin Bot Paroli",
        help_text="Telegram botda /admin buyrug'i uchun parol"
    )
    order_counter = models.BigIntegerField(
        default=0,
        verbose_name="Buyurtma Raqam Hisoblagichi",
        help_text="Oxirgi buyurtma tartib raqami"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bot Sozlamasi"
        verbose_name_plural = "Bot Sozlamalari"

    def __str__(self):
        return f"Bot Sozlamalari (Guruh ID: {self.target_group_id or 'Sozlanmagan'})"
