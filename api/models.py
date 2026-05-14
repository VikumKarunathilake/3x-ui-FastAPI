from typing import Optional
from pydantic import BaseModel


# ─────────────────────────────────────────
# Client Traffics
# ─────────────────────────────────────────
class ClientTrafficBase(BaseModel):
    id: int
    inbound_id: int
    enable: bool
    email: str
    up: int
    down: int
    expiry_time: int
    total: int
    reset: int
    all_time: Optional[int] = 0
    last_online: Optional[int] = 0

# ─────────────────────────────────────────
# Inbound Client IPs  (READ-ONLY — populated by 3x-ui)
# ─────────────────────────────────────────
class InboundClientIP(BaseModel):
    id: int
    client_email: str
    ip: str

# ─────────────────────────────────────────
# Outbound Traffics  (READ-ONLY — populated by 3x-ui)
# ─────────────────────────────────────────
class OutboundTraffic(BaseModel):
    id: int
    tag: str
    up: int
    down: int
    all_time: Optional[int] = 0


# ─────────────────────────────────────────
# Client Activity (from client.db — access log collector)
# ─────────────────────────────────────────
class ClientIP(BaseModel):
    id: int
    client_id: int
    ip: str
    first_seen: str
    last_seen: str
    hit_count: int

class ClientActivityEntry(BaseModel):
    id: int
    client_id: int
    timestamp: str
    protocol: str
    destination: str
    route: str

class ClientSummary(BaseModel):
    id: int
    email: str
    ip_count: int
    activity_count: int

class ClientDetail(BaseModel):
    id: int
    email: str
    ips: list[ClientIP]
    recent_activity: list[ClientActivityEntry]


# ─────────────────────────────────────────
# Client Usage Snapshots (hourly traffic snapshots)
# ─────────────────────────────────────────
class UsageSnapshot(BaseModel):
    id: int
    email: str
    snapshot_ts: str
    up: int
    down: int
    total_quota: int
    enable: int

class DailyUsage(BaseModel):
    email: str
    date: str
    up_used: int
    down_used: int
    total_used: int

class MonthlyUsageSummary(BaseModel):
    email: str
    month: str
    up_used: int
    down_used: int
    total_used: int
    snapshot_count: int
