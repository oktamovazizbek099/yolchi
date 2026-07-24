# 🚖 #2bot - Taxi Group Dispatcher System (Django + Telegram Bot)

Ushbu loyiha Telegram guruhlaridagi yo'lovchilar e'lonlarini (masalan: *"Toshkentga 9:30 da ketishim kerak"*) avtomatik ushlab olib, ularni ro'yxatdan o'tgan **haydovchilarga** yuboruvchi **Django Web Admin + Telegram Bot** tizimidir.

---

## 🏗 Loyiha Tuzilishi (Architecture)

```
D:\#2bot\
  ├── .env                  # Bot Token va Django Secret Key sozlamalari
  ├── manage.py             # Django boshqaruv fayli
  ├── run_web.bat           # Web server va Admin panelni ishga tushirish (1-click)
  ├── run_bot.bat           # Telegram Botni ishga tushirish (1-click)
  ├── create_superadmin.py  # Boshlang'ich admin va operatorlarni yaratish
  ├── core/                 # Django asosiy sozlamalari (settings.py, urls.py, wsgi.py)
  ├── apps/
  │    └── main/            # Foydalanuvchilar (Operator, Haydovchi), E'lonlar va BotSozlamalari modellari
  ├── bot/
  │    ├── main.py          # Aiogram 3 Telegram bot asosiy ishga tushirish fayli
  │    ├── handlers/        # Start, Operator, Haydovchi va Guruh listener buyruqlari
  │    └── utils/           # Django ORM va Bot o'rtasidagi async bog'lanish (db_api.py)
  └── templates/            # Web Dashboard paneli (dashboard.html)
```

---

## 👥 Foydalanuvchilar Rolari va Avtorizatsiya

### 1. 👑 Superadmin (Web Admin)
- Web brauzer orqali `http://127.0.0.1:8000/admin/` manziliga kiradi.
- Operatorlarni yaratadi va har bir operatorga **Telegram Bot Parolini** (`operator_password`) belgilaydi.
- Haydovchilar ro'yxati, telefon raqamlari va e'lonlar statistikasini to'liq nazorat qiladi.

### 2. 🎧 Operator (Telegram Bot & Web)
- Telegram botda `/start` tugmasini bosgach, **"🔑 Operator sifatida kirish"** bo'limini tanlaydi.
- Web panelda Superadmin tomonidan berilgan **Parolni** kiritadi.
- Parol to'g'ri bo'lsa, Telegram botda Operator paneli ochiladi:
  - 📥 **Kutilayotgan e'lonlar:** Guruhdan tushgan yangi yo'lovchi xabarlarini ko'rish va haydovchilarga yuborish.
  - 🚗 **Haydovchilar:** Aktiv haydovchilar soni va ro'yxatini ko'rish.

### 3. 🚗 Haydovchilar (Drivers)
- Botda `/start` bossa, **"📲 Haydovchi bo'lib ro'yxatdan o'tish"** (telefon raqamini yuborish) tugmasi chiqadi.
- Telefon raqami yuborilgach, haydovchi bazaga saqlanadi.
- Guruhga yangi yo me'lon tushganda, bot orqali haydovchiga yo'lovchining matni va bog'lanish ma'lumotlari (telefon / telegram nick) keladi.

### 4. 👥 Guruh Yo'lovchilari (Telegram Group)
- Bot guruhda bo'ladi va yo'lovchilar yozgan xabarlarni tutib oladi.
- Guruh xabari bazaga e'lon sifatida saqlanadi va operator paneliga yoki avtomatik haydovchilarga yuboriladi.

---

## 🚀 Ishga Tushirish Yo'riqnomasi

### 1. `.env` faylida Telegram Bot Tokeningizni kiriting:
`D:\#2bot\.env` faylini oching va `BOT_TOKEN` qiymatiga bot tokeningizni yozing:
```env
BOT_TOKEN=7777777777:AAEb...YOUR_TELEGRAM_BOT_TOKEN...
```

### 2. Web Panelni ishga tushirish:
`D:\#2bot\run_web.bat` faylini ikki marta bosing.
- Django migratsiyalar bajariladi.
- Boshlang'ich `admin` (parol: `admin123`) yaratiladi.
- Server `http://127.0.0.1:8000/` va Admin panel `http://127.0.0.1:8000/admin/` manzilida ishga tushadi.

### 3. Telegram Botni ishga tushirish:
`D:\#2bot\run_bot.bat` faylini ikki marta bosing.
- Bot Telegram bilan bog'lanadi va xabarlarni qabul qilishni boshlaydi.
