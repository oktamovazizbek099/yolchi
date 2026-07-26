from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import (
    Announcement,
    AnnouncementStatus,
    BotSetting,
    GroupType,
    RoleChoices,
    TelegramGroup,
    User,
)


def staff_required(view):
    """Panelga faqat xodimlar (superadmin/operator) kira oladi."""
    decorated = user_passes_test(
        lambda u: u.is_active and (u.is_staff or u.is_superuser),
        login_url='login',
    )(view)
    return login_required(decorated, login_url='login')


def _base_context(request, active):
    return {
        'active': active,
        'user_obj': request.user,
    }


@staff_required
def dashboard_view(request):
    settings_obj, _ = BotSetting.objects.get_or_create(id=1)

    ctx = _base_context(request, 'dashboard')
    ctx.update({
        'total_drivers': User.objects.filter(role=RoleChoices.DRIVER).count(),
        'active_drivers': User.objects.filter(
            role=RoleChoices.DRIVER, is_driver_active=True, is_active=True
        ).count(),
        'total_operators': User.objects.filter(role=RoleChoices.OPERATOR).count(),
        'total_announcements': Announcement.objects.count(),
        'accepted_count': Announcement.objects.filter(
            status=AnnouncementStatus.ACCEPTED
        ).count(),
        'passenger_groups': TelegramGroup.objects.filter(
            group_type=GroupType.PASSENGER, is_active=True
        ).count(),
        'driver_groups': TelegramGroup.objects.filter(
            group_type=GroupType.DRIVER, is_active=True
        ).count(),
        'recent_announcements': Announcement.objects.select_related(
            'accepted_by_driver'
        ).all()[:15],
        'bot_settings': settings_obj,
    })
    return render(request, 'dashboard.html', ctx)


# ========================================
# GURUHLAR
# ========================================

@staff_required
def groups_view(request):
    ctx = _base_context(request, 'groups')
    ctx.update({
        'passenger_groups': TelegramGroup.objects.filter(group_type=GroupType.PASSENGER),
        'driver_groups': TelegramGroup.objects.filter(group_type=GroupType.DRIVER),
    })
    return render(request, 'groups.html', ctx)


@staff_required
@require_POST
def group_add(request):
    chat_id = (request.POST.get('chat_id') or '').strip()
    title = (request.POST.get('title') or '').strip()
    group_type = request.POST.get('group_type')

    if group_type not in (GroupType.PASSENGER, GroupType.DRIVER):
        messages.error(request, "Guruh turi noto'g'ri.")
        return redirect('groups')

    try:
        chat_id_int = int(chat_id)
    except ValueError:
        messages.error(
            request,
            "Chat ID butun son bo'lishi kerak (masalan -1001234567890). "
            "ID ni bilish uchun guruhda /id buyrug'ini yuboring."
        )
        return redirect('groups')

    group, created = TelegramGroup.objects.update_or_create(
        chat_id=chat_id_int,
        defaults={
            'title': title,
            'group_type': group_type,
            'is_active': True,
            'added_by': request.user,
        },
    )
    messages.success(
        request,
        f"Guruh {'qo`shildi' if created else 'yangilandi'}: {group.title or group.chat_id}"
    )
    return redirect('groups')


@staff_required
@require_POST
def group_toggle(request, group_id):
    group = get_object_or_404(TelegramGroup, id=group_id)
    group.is_active = not group.is_active
    group.save()
    messages.success(
        request,
        f"{group.title or group.chat_id}: "
        f"{'aktivlashtirildi' if group.is_active else 'ochirildi'}"
    )
    return redirect('groups')


@staff_required
@require_POST
def group_delete(request, group_id):
    group = get_object_or_404(TelegramGroup, id=group_id)
    name = group.title or str(group.chat_id)
    group.delete()
    messages.success(request, f"Guruh o'chirildi: {name}")
    return redirect('groups')


# ========================================
# HAYDOVCHILAR
# ========================================

@staff_required
def drivers_view(request):
    ctx = _base_context(request, 'drivers')
    ctx['drivers'] = User.objects.filter(role=RoleChoices.DRIVER).order_by('-id')
    return render(request, 'drivers.html', ctx)


@staff_required
@require_POST
def driver_toggle(request, user_id):
    driver = get_object_or_404(User, id=user_id, role=RoleChoices.DRIVER)
    driver.is_active = not driver.is_active
    driver.save()
    messages.success(
        request,
        f"{driver.first_name or driver.username}: "
        f"{'aktivlashtirildi' if driver.is_active else 'bloklandi'}"
    )
    return redirect('drivers')


@staff_required
@require_POST
def driver_delete(request, user_id):
    driver = get_object_or_404(User, id=user_id, role=RoleChoices.DRIVER)
    name = driver.first_name or driver.username
    driver.delete()
    messages.success(request, f"Haydovchi o'chirildi: {name}")
    return redirect('drivers')


# ========================================
# BUYURTMALAR
# ========================================

@staff_required
def orders_view(request):
    status = request.GET.get('status')
    qs = Announcement.objects.select_related('accepted_by_driver').all()
    if status in dict(AnnouncementStatus.choices):
        qs = qs.filter(status=status)

    ctx = _base_context(request, 'orders')
    ctx.update({
        'orders': qs[:100],
        'status_choices': AnnouncementStatus.choices,
        'current_status': status or '',
    })
    return render(request, 'orders.html', ctx)


# ========================================
# SOZLAMALAR
# ========================================

@staff_required
def settings_view(request):
    setting, _ = BotSetting.objects.get_or_create(id=1)

    if request.method == 'POST':
        setting.auto_broadcast = request.POST.get('auto_broadcast') == 'on'
        setting.smart_filter = request.POST.get('smart_filter') == 'on'

        try:
            setting.min_order_length = max(1, int(request.POST.get('min_order_length') or 10))
        except ValueError:
            setting.min_order_length = 10

        password = (request.POST.get('superadmin_bot_password') or '').strip()
        if password:
            setting.superadmin_bot_password = password

        setting.save()
        messages.success(request, "Sozlamalar saqlandi.")
        return redirect('settings')

    ctx = _base_context(request, 'settings')
    ctx['bot_settings'] = setting
    return render(request, 'settings.html', ctx)
