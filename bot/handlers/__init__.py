from .start import router as start_router
from .operator import router as operator_router
from .driver import router as driver_router
from .group import router as group_router

routers = [start_router, operator_router, driver_router, group_router]
