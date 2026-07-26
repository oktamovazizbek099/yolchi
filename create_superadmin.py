"""
Boshlang'ich foydalanuvchilarni yaratish.

Parollarni .env orqali berish mumkin:
  ADMIN_PASSWORD          — web panelga kirish paroli (default: admin123)
  SUPERADMIN_BOT_PASSWORD — Telegram botda /admin uchun parol (default: admin12345)
  OPERATOR_BOT_PASSWORD   — operatorning bot paroli (default: op12345password)
"""
import os
import sys

import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dotenv import load_dotenv  # noqa: E402

from apps.main.models import BotSetting, RoleChoices, User  # noqa: E402

load_dotenv()

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
SUPERADMIN_BOT_PASSWORD = os.getenv('SUPERADMIN_BOT_PASSWORD', 'admin12345')
OPERATOR_BOT_PASSWORD = os.getenv('OPERATOR_BOT_PASSWORD', 'op12345password')


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
        admin_user.set_password(ADMIN_PASSWORD)
        admin_user.operator_password = SUPERADMIN_BOT_PASSWORD
        admin_user.save()
        print(f"✅ Superadmin yaratildi.  Web login: admin | parol: {ADMIN_PASSWORD}")
        print(f"   Telegram /admin paroli: {SUPERADMIN_BOT_PASSWORD}")
    else:
        # Bot paroli yo'q bo'lsa to'ldiramiz (eski bazalar uchun)
        if not admin_user.operator_password:
            admin_user.operator_password = SUPERADMIN_BOT_PASSWORD
            admin_user.save()
            print(f"ℹ️ Superadminga bot paroli qo'shildi: {SUPERADMIN_BOT_PASSWORD}")
        else:
            print("ℹ️ Superadmin 'admin' allaqachon mavjud.")

    # 2. Namuna operator
    op_user, created_op = User.objects.get_or_create(
        username='operator1',
        defaults={
            'first_name': 'Operator',
            'last_name': 'Birinchi',
            'role': RoleChoices.OPERATOR,
            'operator_password': OPERATOR_BOT_PASSWORD,
            'is_staff': True,
        }
    )
    if created_op:
        op_user.set_password('operator123')
        op_user.save()
        print(f"✅ Operator 'operator1' yaratildi. Bot paroli: {OPERATOR_BOT_PASSWORD}")
    else:
        print("ℹ️ Operator 'operator1' allaqachon mavjud.")

    # 3. Bot sozlamalari qatori
    setting, created_set = BotSetting.objects.get_or_create(id=1)
    if not setting.superadmin_bot_password:
        setting.superadmin_bot_password = SUPERADMIN_BOT_PASSWORD
        setting.save()
    if created_set:
        print("✅ Bot sozlamalari yaratildi.")


if __name__ == '__main__':
    create_initial_users()
