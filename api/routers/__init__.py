from .client_traffics import router as client_traffics
from .client_ips import router as client_ips
from .outbound_traffics import router as outbound_traffics
from .clients import router as clients
from .settings import router as settings
from .users import router as users

__all__ = [
    "client_traffics",
    "client_ips",
    "outbound_traffics",
    "clients",
    "settings",
    "users",
]
