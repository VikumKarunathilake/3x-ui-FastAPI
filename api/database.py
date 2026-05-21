# pyright: ignore [reportMissingImports]
import aiosqlite
from contextlib import asynccontextmanager
from typing import Dict, Optional
from api.config import settings
import time


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(
        f"file:{settings.full_db_path.as_posix()}?mode=ro", uri=True
    ) as db:
        db.row_factory = aiosqlite.Row
        yield db


@asynccontextmanager
async def get_traffic_db():
    async with aiosqlite.connect(
        f"file:{settings.full_traffic_db_path.as_posix()}?mode=ro", uri=True
    ) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_traffic_db():
    """Create traffic.db and define client_ips schema"""
    db_path = settings.full_traffic_db_path
    if not db_path.exists():
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS client_ips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    email TEXT,
                    ip TEXT,
                    last_seen TEXT,
                    UNIQUE(email, ip)
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_client_ips_email ON client_ips(email)"
            )
            await db.commit()


_cache: Dict[str, tuple] = {}


async def _get_client_cached(key: str, query: str, val: any) -> Optional[Dict]:
    now = time.time()
    if key in _cache:
        data, ts = _cache[key]
        if now - ts < settings.CACHE_TTL:
            return data

    async with get_db() as db:
        async with db.execute(query, (val,)) as cursor:
            row = await cursor.fetchone()
            res = dict(row) if row else None
            if res:
                _cache[f"email:{res['email']}"] = (res, now)
                _cache[f"id:{res['id']}"] = (res, now)
            else:
                _cache[key] = (None, now)
            return res


async def get_client_by_email(email: str) -> Optional[Dict]:
    return await _get_client_cached(
        f"email:{email}", "SELECT * FROM client_traffics WHERE email = ?", email
    )


async def get_client_by_id(client_id: int) -> Optional[Dict]:
    return await _get_client_cached(
        f"id:{client_id}", "SELECT * FROM client_traffics WHERE id = ?", client_id
    )
