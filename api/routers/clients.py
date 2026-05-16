from fastapi import APIRouter, HTTPException
from api.schemas import ClientTraffic
from api.database import (
    get_client_by_email,
    get_client_by_id,
)

router = APIRouter(prefix="/clients", tags=["clients"])


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
