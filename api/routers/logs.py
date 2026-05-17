from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from api.database import get_traffic_db, get_client_by_id
from api.schemas import ClientIP

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/ips/{client_id}", response_model=List[ClientIP])
async def get_client_ips_by_id(
    client_id: int,
):
    """Get all unique IPs seen for a specific user ID"""
    client = await get_client_by_id(client_id)
    if not client or "email" not in client:
        raise HTTPException(
            status_code=404, detail=f"Client with ID {client_id} not found"
        )
    email = client["email"]

    query = "SELECT * FROM client_ips WHERE email = ? ORDER BY last_seen DESC"
    try:
        async with get_traffic_db() as db:
            async with db.execute(query, (email,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
