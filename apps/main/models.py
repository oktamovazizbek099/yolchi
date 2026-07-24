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


class AnnouncementStatus(models.TextChoices):
    NEW = 'NEW', 'Yangi (Kutilmoqda)'
    BROADCASTED = 'BROADCASTED', 'Haydovchilarga Yuborildi'
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


class BotSetting(models.Model):
    target_group_id = models.BigIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Kuzatiladigan Guruh Telegram ID",
        help_text="Masalan: -100123456789 (Bot guruhda admin bo'lishi kerak)"
    )
    auto_broadcast = models.BooleanField(
        default=False, 
        verbose_name="Avtomatik Haydovchilarga Yuborish",
        help_text="Belgilansa, guruhga tushgan e'lon operator tasdig'isiz birdaniga barcha haydovchilarga yuboriladi"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bot Sozlamasi"
        verbose_name_plural = "Bot Sozlamalari"

    def __str__(self):
        return f"Bot Sozlamalari (Guruh ID: {self.target_group_id or 'Sozlanmagan'})"
