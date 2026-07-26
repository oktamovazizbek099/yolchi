"""
Yo'lovchilar guruhidagi xabarni buyurtma deb hisoblash yoki hisoblamaslikni aniqlovchi
aqlli filtr. Maqsad: "salom", "rahmat", "👍", "ok" kabi gaplar buyurtmaga aylanmasin.
"""
import re

# Buyurtma emas — shunchaki muloqot
STOP_PHRASES = {
    "salom", "assalomu alaykum", "assalomu aleykum", "assalom", "alaykum assalom",
    "va alaykum assalom", "vaalaykum assalom", "hayrli tong", "xayrli tong",
    "hayrli kun", "xayrli kun", "hayrli kech", "xayrli kech", "hayrli tun",
    "rahmat", "raxmat", "katta rahmat", "tashakkur", "ok", "okay", "xo'p", "xop",
    "mayli", "ha", "yo'q", "yoq", "yaxshi", "zo'r", "zor", "bo'ldi", "boldi",
    "keldi", "ketdim", "ketdi", "boraman", "olaman", "bor", "yo'lda", "yolda",
    "qale", "qalesiz", "qandaysiz", "salomat bo'ling", "xayr", "hayr",
    "kutaman", "kutyapman", "tez", "tezroq", "hozir", "hoziroq", "bo'sh", "bosh",
    "band", "bandman", "bo'shman", "boshman", "javob bering", "?", "??", "???",
    "test", "tekshiruv", "reklama", "admin", "operator",
}

# Harf yoki raqam bormi (faqat emoji / stiker matnini rad etish uchun)
HAS_WORD_CHAR = re.compile(r'[0-9a-zA-ZЀ-ӿĀ-ɏ]')

# Havola va forward-spam belgilari
LINK_RE = re.compile(r'(https?://|t\.me/|telegram\.me/|@[a-zA-Z0-9_]{5,})')


def normalize(text: str) -> str:
    """Taqqoslash uchun matnni soddalashtirish."""
    t = text.strip().lower()
    t = t.replace('ʻ', "'").replace('ʼ', "'").replace('`', "'").replace('’', "'")
    t = re.sub(r'[!.,;:\-–—_*"()\[\]]+', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def is_order_message(text: str, min_length: int = 10, smart: bool = True):
    """
    Xabar buyurtma sifatida qabul qilinsinmi?

    Returns: (bool, sabab)
      sabab — rad etilgan bo'lsa logga yozish uchun qisqa izoh.
    """
    if not text:
        return False, "bo'sh xabar"

    raw = text.strip()

    # Bot buyruqlari hech qachon buyurtma emas
    if raw.startswith('/'):
        return False, "buyruq"

    if not smart:
        return True, "filtr o'chirilgan"

    # Harf/raqamsiz — faqat emoji yoki belgilar
    if not HAS_WORD_CHAR.search(raw):
        return False, "faqat emoji/belgi"

    # Faqat havola tashlangan bo'lsa (reklama) — xom matn ustidan tekshiriladi,
    # chunki normalize() ':' va '/' belgilarini olib tashlaydi.
    without_links = LINK_RE.sub(' ', raw).strip()
    if len(re.sub(r'\s+', ' ', without_links)) < min_length:
        return False, "faqat havola/reklama"

    norm = normalize(raw)

    # Juda qisqa
    if len(norm) < min_length:
        return False, f"juda qisqa ({len(norm)} < {min_length})"

    # Bir so'zli xabarlar buyurtma bo'la olmaydi
    words = norm.split()
    if len(words) < 2:
        return False, "bitta so'z"

    # Tayyor salomlashish / javob iboralari
    if norm in STOP_PHRASES:
        return False, "salomlashish/javob"

    # "salom" + emoji kabi holatlar: barcha so'zlar stop-ro'yxatda bo'lsa
    if all(w in STOP_PHRASES for w in words):
        return False, "faqat muloqot so'zlari"

    return True, "ok"
