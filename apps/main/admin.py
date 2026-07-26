from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Announcement, BotSetting, BroadcastMessage, TelegramGroup


@admin.register(TelegramGroup)
class TelegramGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'chat_id', 'group_type', 'is_active', 'added_by', 'created_at')
    list_filter = ('group_type', 'is_active')
    search_fields = ('title', 'chat_id')
    list_editable = ('is_active',)


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'announcement', 'chat_id', 'message_id', 'is_group', 'created_at')
    list_filter = ('is_group',)
    search_fields = ('chat_id', 'announcement__id')

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
        'status', 'accepted_by_driver', 'accepted_at',
        'created_by_operator', 'created_at'
    )
    list_filter = ('status', 'created_at', 'accepted_by_driver')
    search_fields = ('passenger_name', 'passenger_phone', 'raw_text', 'from_location', 'to_location')
    readonly_fields = ('created_at', 'accepted_by_driver', 'accepted_at', 'drivers_group_message_id', 'source_group_id', 'source_group_name')
    ordering = ('-created_at',)


@admin.register(BotSetting)
class BotSettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'auto_broadcast', 'smart_filter', 'min_order_length',
                    'order_counter', 'updated_at')
