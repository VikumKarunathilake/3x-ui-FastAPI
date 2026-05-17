from pydantic import BaseModel
from typing import Optional


class ClientTraffic(BaseModel):
    id: Optional[int] = None
    inbound_id: Optional[int] = None
    enable: Optional[int] = None
    email: Optional[str] = None
    up: Optional[int] = None
    down: Optional[int] = None
    all_time: Optional[int] = None
    expiry_time: Optional[int] = None
    total: Optional[int] = None
    reset: Optional[int] = None
    last_online: Optional[int] = None


class ClientIP(BaseModel):
    id: Optional[int] = None
    email: str
    ip: str
    last_seen: str
