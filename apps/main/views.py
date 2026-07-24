from django.shortcuts import render
from django.db.models import Count
from .models import User, Announcement, RoleChoices, AnnouncementStatus

def dashboard_view(request):
    total_operators = User.objects.filter(role=RoleChoices.OPERATOR).count()
    total_drivers = User.objects.filter(role=RoleChoices.DRIVER, is_driver_active=True).count()
    total_announcements = Announcement.objects.count()
    recent_announcements = Announcement.objects.select_related('created_by_operator').all()[:10]

    context = {
        'total_operators': total_operators,
        'total_drivers': total_drivers,
        'total_announcements': total_announcements,
        'recent_announcements': recent_announcements,
    }
    return render(request, 'dashboard.html', context)
