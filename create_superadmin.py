"""
Boshlang'ich foydalanuvchilarni yaratish va parollarni sinxronlash.

Parollar .env / Railway env orqali beriladi:
  ADMIN_PASSWORD          — web panelga kirish paroli
  SUPERADMIN_BOT_PASSWORD — Telegram botda /admin uchun parol
  OPERATOR_BOT_PASSWORD   — operatorning bot paroli

MUHIM: agar bu o'zgaruvchilar berilgan bo'lsa, ular ASOSIY manba hisoblanadi va
har deployda mavjud foydalanuvchiga ham qo'llanadi. Aks holda bir marta standart
parol bilan yaratilgan hisob abadiy o'sha parolda qolib ketardi.

Parolni panel orqali o'zgartirmoqchi bo'lsangiz — avval Railway'dagi env
qiymatini yangilang, aks holda keyingi deployda eskisiga qaytadi.
"""
import os
import sys

import django

# Windows konsoli (cp1251) emoji'da yiqilib, skriptni yarim yo'lda to'xtatib
# qo'ymasligi uchun. Railway'da (UTF-8) baribir ta'siri yo'q.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dotenv import load_dotenv  # noqa: E402

from apps.main.models import BotSetting, RoleChoices, User  # noqa: E402

load_dotenv()

# Env'da berilganmi? Berilgan bo'lsa mavjud hisoblarga ham majburan qo'llanadi.
ADMIN_PASSWORD_ENV = os.getenv('ADMIN_PASSWORD')
SUPERADMIN_BOT_PASSWORD_ENV = os.getenv('SUPERADMIN_BOT_PASSWORD')
OPERATOR_BOT_PASSWORD_ENV = os.getenv('OPERATOR_BOT_PASSWORD')

ADMIN_PASSWORD = ADMIN_PASSWORD_ENV or 'admin123'
SUPERADMIN_BOT_PASSWORD = SUPERADMIN_BOT_PASSWORD_ENV or 'admin12345'
OPERATOR_BOT_PASSWORD = OPERATOR_BOT_PASSWORD_ENV or 'op12345password'


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
        print("✅ Superadmin yaratildi (login: admin).")
    else:
        changed = []
        # Env'da parol berilgan bo'lsa — u asosiy manba
        if ADMIN_PASSWORD_ENV and not admin_user.check_password(ADMIN_PASSWORD_ENV):
            admin_user.set_password(ADMIN_PASSWORD_ENV)
            changed.append('web paroli')
        if SUPERADMIN_BOT_PASSWORD_ENV and \
                admin_user.operator_password != SUPERADMIN_BOT_PASSWORD_ENV:
            admin_user.operator_password = SUPERADMIN_BOT_PASSWORD_ENV
            changed.append('bot paroli')
        elif not admin_user.operator_password:
            admin_user.operator_password = SUPERADMIN_BOT_PASSWORD
            changed.append('bot paroli')

        if changed:
            admin_user.save()
            print(f"🔑 Superadmin parollari env'dan yangilandi: {', '.join(changed)}")
        else:
            print("ℹ️ Superadmin 'admin' o'zgarishsiz.")

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
        op_user.set_password(OPERATOR_BOT_PASSWORD)
        op_user.save()
        print("✅ Operator 'operator1' yaratildi.")
    elif OPERATOR_BOT_PASSWORD_ENV and op_user.operator_password != OPERATOR_BOT_PASSWORD_ENV:
        op_user.operator_password = OPERATOR_BOT_PASSWORD_ENV
        op_user.set_password(OPERATOR_BOT_PASSWORD_ENV)
        op_user.save()
        print("🔑 Operator paroli env'dan yangilandi.")
    else:
        print("ℹ️ Operator 'operator1' o'zgarishsiz.")

    # 3. Bot sozlamalari qatori
    setting, created_set = BotSetting.objects.get_or_create(id=1)
    if SUPERADMIN_BOT_PASSWORD_ENV and \
            setting.superadmin_bot_password != SUPERADMIN_BOT_PASSWORD_ENV:
        setting.superadmin_bot_password = SUPERADMIN_BOT_PASSWORD_ENV
        setting.save()
    elif not setting.superadmin_bot_password:
        setting.superadmin_bot_password = SUPERADMIN_BOT_PASSWORD
        setting.save()
    if created_set:
        print("✅ Bot sozlamalari yaratildi.")


if __name__ == '__main__':
    create_initial_users()
