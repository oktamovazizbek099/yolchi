import os
import sys
import django

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.main.models import User, RoleChoices

def create_initial_users():
    # 1. Superadmin
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'first_name': 'Super',
            'last_name': 'Admin',
            'email': 'admin@example.com',
            'role': RoleChoices.SUPERADMIN,
            'is_staff': True,
            'is_superuser': True,
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("✅ Superadmin yaratildi! Login: admin | Parol: admin123")
    else:
        print("ℹ️ Superadmin 'admin' allaqachon mavjud.")

    # 2. Example Operator
    op_user, created_op = User.objects.get_or_create(
        username='operator1',
        defaults={
            'first_name': 'Operator',
            'last_name': 'Birinchi',
            'role': RoleChoices.OPERATOR,
            'operator_password': 'op12345password',
            'is_staff': True,
        }
    )
    if created_op:
        op_user.set_password('operator123')
        op_user.save()
        print("✅ Operator 'operator1' yaratildi! Telegram Bot Paroli: op12345password")
    else:
        print("ℹ️ Operator 'operator1' allaqachon mavjud.")

if __name__ == '__main__':
    create_initial_users()
