from typing import List
from fastapi import APIRouter, HTTPException
from api.schemas import ClientTraffic
from api.database import (
    get_client_by_email,
    get_client_by_id,
)

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=List[str])
async def list_client_emails():
    """List all available client emails from database"""
    from api.database import get_db
    try:
        async with get_db() as db:
            async with db.execute(
                "SELECT DISTINCT email FROM client_traffics WHERE email IS NOT NULL AND email != '' ORDER BY email ASC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [row["email"] for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{email}", response_model=ClientTraffic)
async def get_client_by_email_endpoint(email: str):
    """Get a specific client by email"""
    client = await get_client_by_email(email)
    if not client:
        raise HTTPException(
            status_code=404, detail=f"Client with email '{email}' not found"
        )
    return ClientTraffic(**client)


@router.get("/id/{client_id}", response_model=ClientTraffic)
async def get_client_by_id_endpoint(client_id: int):
    """Get a specific client by database ID"""
    client = await get_client_by_id(client_id)
    if not client:
        raise HTTPException(
            status_code=404, detail=f"Client with ID '{client_id}' not found"
        )
    return ClientTraffic(**client)
