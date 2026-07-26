"""
Routerlar ro'yxati. TARTIB MUHIM:

1. groupsetup — guruh buyruqlari (/yolovchi_guruh ...) buyurtma tinglovchisidan oldin
2. superadmin (kirish) — /admin va parol
3. superadmin (panel) — faqat superadmin uchun, IsSuperAdmin filtri bilan
4. start — /start, /help, /login
5. operator — operator paneli
6. driver — haydovchi
7. group — yo'lovchilar guruhi tinglovchisi (eng oxirida, keng filtr)
"""
from .groupsetup import router as groupsetup_router
from .superadmin import panel_router as superadmin_panel_router
from .superadmin import router as superadmin_auth_router
from .start import router as start_router
from .operator import router as operator_router
from .driver import router as driver_router
from .group import router as group_router

routers = [
    groupsetup_router,
    superadmin_auth_router,
    superadmin_panel_router,
    start_router,
    operator_router,
    driver_router,
    group_router,
]
