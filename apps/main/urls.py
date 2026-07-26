from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),

    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('guruhlar/', views.groups_view, name='groups'),
    path('guruhlar/qoshish/', views.group_add, name='group_add'),
    path('guruhlar/<int:group_id>/holat/', views.group_toggle, name='group_toggle'),
    path('guruhlar/<int:group_id>/ochirish/', views.group_delete, name='group_delete'),

    path('haydovchilar/', views.drivers_view, name='drivers'),
    path('haydovchilar/<int:user_id>/holat/', views.driver_toggle, name='driver_toggle'),
    path('haydovchilar/<int:user_id>/ochirish/', views.driver_delete, name='driver_delete'),

    path('buyurtmalar/', views.orders_view, name='orders'),
    path('sozlamalar/', views.settings_view, name='settings'),
]
