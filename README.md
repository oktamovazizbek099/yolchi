# 🚖 #2bot — Taxi Group Dispatcher (Django + Telegram Bot)

Yo'lovchilar guruhiga yozilgan buyurtmalarni avtomatik ushlab olib, shablon formatida
**haydovchilar guruhiga** tashlaydigan tizim. Buyurtmani birinchi bo'lib "✅ Zakazni yopish"
tugmasini bosgan haydovchi oladi — va **faqat o'sha haydovchi** yo'lovchining telefoni va
profilini ko'radi.

---

## 🔑 Asosiy qoida: ikki guruh butunlay ajratilgan

```
┌──────────────────────────┐         ┌───────────────────────────┐
│  YO'LOVCHILAR GURUHI     │         │   HAYDOVCHILAR GURUHI     │
│  (bot faqat O'QIYDI)     │  ─────► │   (bot faqat YOZADI)      │
│                          │         │                           │
│  "Axchaga pochta bor"    │         │  🚕 1-BUYURTMA            │
└──────────────────────────┘         │  🧑 Mijoz: Humoyun        │
                                     │  🔒 aloqa yopiq           │
   Bot ro'yxatdagi guruhlardan       │  [✅ Zakazni yopish]      │
   tashqari HECH QAYERDAN            └───────────────────────────┘
   xabar olmaydi.                                │
                                                 │ birinchi bosgan
                                                 ▼
                                     ┌───────────────────────────┐
                                     │  HAYDOVCHIGA SHAXSIY      │
                                     │  📞 +998946656678         │
                                     │  💬 @username             │
                                     │  [🚕 Profil] [🏘 Qo'ng'iroq]│
                                     └───────────────────────────┘
```

**Muhim:** haydovchilar guruhidagi yozishmalar hech qachon buyurtmaga aylanmaydi —
bot faqat `PASSENGER` turidagi ro'yxatdan o'tgan guruhlarni tinglaydi.

---

## 🔒 Aloqa ma'lumotlari maxfiyligi

| Qayerda | Mijoz ismi | Telefon | Username | Profil tugmasi |
|---|---|---|---|---|
| Haydovchilar guruhi | ✅ ko'rinadi | ❌ yopiq | ❌ yopiq | ❌ yo'q |
| Qabul qilgan haydovchiga (shaxsiy) | ✅ | ✅ | ✅ | ✅ |
| Boshqa haydovchilar | ✅ | ❌ | ❌ | ❌ |

Yo'lovchi raqamini xabar matnining ichiga yozsa ham, u guruh matnida
`🔒[raqam yopiq]` ko'rinishida niqoblanadi.

---

## 🏗 Tuzilishi

```
D:\#2bot\
  ├── bot/
  │    ├── main.py              # Aiogram 3 ishga tushirish
  │    ├── handlers/
  │    │    ├── groupsetup.py   # /yolovchi_guruh, /haydovchi_guruh, /id, /holat
  │    │    ├── superadmin.py   # /admin paneli (guruh, haydovchi, statistika)
  │    │    ├── start.py        # /start, /help, /login
  │    │    ├── operator.py     # operator paneli
  │    │    ├── driver.py       # haydovchi ro'yxati, "Mening buyurtmalarim"
  │    │    └── group.py        # yo'lovchi guruhi tinglovchisi + qabul qilish
  │    └── utils/
  │         ├── db_api.py       # Django ORM <-> bot (async)
  │         └── filters.py      # aqlli xabar filtri
  ├── apps/main/                # modellar, web view'lar, admin
  ├── templates/                # web panel (base, dashboard, groups, drivers, orders, settings)
  ├── core/                     # Django settings
  └── create_superadmin.py      # boshlang'ich foydalanuvchilar
```

---

## 🚀 Ishga tushirish

### 1. `.env`
```env
BOT_TOKEN=1234567890:AA...
DJANGO_SECRET_KEY=uzun-tasodifiy-satr
DEBUG=False
ADMIN_PASSWORD=admin123
SUPERADMIN_BOT_PASSWORD=admin12345
```

### 2. Web panel
```
run_web.bat
```
→ `http://127.0.0.1:8000/` — **login talab qilinadi** (`admin` / `admin123`)

### 3. Bot
```
run_bot.bat
```

### 4. Guruhlarni sozlash (bir marta)

1. Botni **yo'lovchilar guruhiga** qo'shing → o'sha guruhda `/yolovchi_guruh` yozing
2. Botni **haydovchilar guruhiga** qo'shing (admin qilib) → `/haydovchi_guruh` yozing
3. Tekshirish: guruhda `/holat`

> Buyruqlarni ishlatish uchun avval botga shaxsiy `/admin` yozib parol bilan kiring.

Yoki web panelda: **Guruhlar → Qo'lda guruh qo'shish** (chat ID ni guruhda `/id` bilan oling).

---

## 👥 Rollar

### 👑 Superadmin
- **Web:** `/` — statistika, guruhlar, haydovchilar, buyurtmalar, sozlamalar
- **Bot:** `/admin` + parol → guruhlarni yoqish/o'chirish, haydovchilarni bloklash, statistika
- Django admin: `/admin/`

### 🎧 Operator
- Botda `/start` → "🔑 Operator sifatida kirish" → web admin bergan parol
- Kutilayotgan buyurtmalarni qo'lda haydovchilarga yuborish
- Web panelga ham kira oladi (`is_staff`)

### 🚗 Haydovchi
- Botda `/start` → telefon raqamni yuborish
- Haydovchilar guruhida "✅ Zakazni yopish" bosib buyurtma oladi
- "📋 Mening buyurtmalarim" — olgan buyurtmalari va mijoz aloqasi

---

## 🧠 Aqlli filtr

Yo'lovchilar guruhidagi har bir xabar buyurtma emas. O'tkazib yuboriladi:

| Xabar | Natija |
|---|---|
| `Axchaga pochta bor edi` | ✅ buyurtma |
| `Toshkent 2 kishi` | ✅ buyurtma |
| `salom` / `rahmat` / `ok` | ⏭ o'tkazildi |
| `👍👍👍` | ⏭ o'tkazildi |
| `/start` | ⏭ o'tkazildi |
| `https://t.me/kanal` | ⏭ o'tkazildi |

Sozlash: web panel → **Sozlamalar** (minimal uzunlik, filtrni o'chirish).

---

## ⚙️ Sozlamalar

| Sozlama | Ma'nosi |
|---|---|
| **Aqlli filtr** | Salomlashish/emoji xabarlarini o'tkazib yuborish |
| **Minimal uzunlik** | Shundan qisqa xabarlar buyurtma emas (default 10) |
| **Shaxsiy xabar** | Buyurtmani guruhdan tashqari har bir haydovchiga shaxsiy ham yuborish |
| **Superadmin bot paroli** | `/admin` buyrug'i uchun parol |

---

## ⚠️ Deploy uchun eslatma

- **SQLite Railway'da vaqtinchalik** — har deploydan keyin ma'lumotlar yo'qoladi.
  Ishlab chiqarish uchun Postgres ulash kerak.
- `start.sh` botni fon jarayonida ishga tushiradi — bot yiqilsa Railway sezmaydi.
  Bot va webni **alohida service** qilish tavsiya etiladi.
