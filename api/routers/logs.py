from fastapi import APIRouter, HTTPException
from typing import List
from api.database import get_traffic_db, get_client_by_id
from api.schemas import ClientIP, ClientTrafficSnapshot, TrafficStatsResponse
from api.collector import get_traffic_aggregation

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


@router.get("/traffic-snapshots/{email}", response_model=List[ClientTrafficSnapshot])
async def get_client_traffic_snapshots(email: str):
    """Get all raw traffic snapshots for a specific email"""
    query = "SELECT * FROM client_traffic_snapshots WHERE email = ? ORDER BY timestamp DESC"
    try:
        async with get_traffic_db() as db:
            async with db.execute(query, (email,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traffic-stats/{email}", response_model=TrafficStatsResponse)
async def get_client_traffic_stats(email: str):
    """Get aggregated daily, weekly, and monthly traffic stats for a specific email"""
    try:
        res = await get_traffic_aggregation(email)
        return TrafficStatsResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
