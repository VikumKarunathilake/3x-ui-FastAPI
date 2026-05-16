# pyright: ignore [reportMissingImports]
import aiosqlite
from contextlib import asynccontextmanager
from typing import Dict, Optional
from api.config import settings


@asynccontextmanager
async def get_db():
    """Async database connection context manager"""
    async with aiosqlite.connect(
        f"file:{settings.full_db_path.as_posix()}?mode=ro", uri=True
    ) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def get_client_by_email(email: str) -> Optional[Dict]:
    """Get single client by email"""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM client_traffics WHERE email = ?", (email,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_client_by_id(client_id: int) -> Optional[Dict]:
    """Get single client by database ID"""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM client_traffics WHERE id = ?", (client_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
