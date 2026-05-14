from fastapi import APIRouter, HTTPException
from api.database import get_db_read
from api.models import ClientTrafficBase

router = APIRouter(prefix="/client-traffics", tags=["Client Traffics"])


@router.get("/", summary="List all client traffics", response_model=list[ClientTrafficBase])
def list_client_traffics():
    with get_db_read() as db:
        rows = db.execute("SELECT * FROM client_traffics").fetchall()
        return [dict(r) for r in rows]


@router.get("/{traffic_id}", summary="Get client traffic by ID", response_model=ClientTrafficBase)
def get_client_traffic(traffic_id: int):
    with get_db_read() as db:
        row = db.execute(
            "SELECT * FROM client_traffics WHERE id = ?", (traffic_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Client traffic not found")
        return dict(row)


@router.get("/by-email/{email}", summary="Get client traffic by email", response_model=ClientTrafficBase)
def get_client_traffic_by_email(email: str):
    with get_db_read() as db:
        row = db.execute(
            "SELECT * FROM client_traffics WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Client traffic not found")
        return dict(row)
