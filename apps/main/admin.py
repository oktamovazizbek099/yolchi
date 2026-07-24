from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Announcement, BotSetting

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'id', 'username', 'get_full_name', 'role', 
        'phone_number', 'telegram_id', 'operator_password', 
        'is_driver_active', 'is_telegram_authenticated'
    )
    list_filter = ('role', 'is_driver_active', 'is_telegram_authenticated', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'phone_number', 'telegram_id', 'operator_password')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Tizim Roli va Telegram Ma\'lumotlari', {
            'fields': (
                'role', 
                'telegram_id', 
                'phone_number', 
                'operator_password', 
                'is_driver_active', 
                'is_telegram_authenticated'
            )
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Tizim Roli va Telegram Ma\'lumotlari', {
            'fields': (
                'role', 
                'telegram_id', 
                'phone_number', 
                'operator_password', 
                'is_driver_active'
            )
        }),
    )


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'passenger_name', 'passenger_phone', 
        'from_location', 'to_location', 'departure_time', 
        'status', 'created_by_operator', 'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('passenger_name', 'passenger_phone', 'raw_text', 'from_location', 'to_location')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(BotSetting)
class BotSettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'target_group_id', 'auto_broadcast', 'updated_at')
