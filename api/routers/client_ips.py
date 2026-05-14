from fastapi import APIRouter, HTTPException
from api.database import get_db_read
from api.models import InboundClientIP

router = APIRouter(prefix="/client-ips", tags=["Client IPs"])

# ── READ-ONLY ──────────────────────────────────────────────────────
# Client IP records are populated by 3x-ui as clients connect.
# This API only exposes GET endpoints for monitoring.
# ───────────────────────────────────────────────────────────────────


@router.get("/", summary="List all client IPs", response_model=list[InboundClientIP])
def list_client_ips():
    with get_db_read() as db:
        rows = db.execute("SELECT * FROM inbound_client_ips").fetchall()
        return [dict(r) for r in rows]


@router.get("/{ip_id}", summary="Get client IP record by ID", response_model=InboundClientIP)
def get_client_ip(ip_id: int):
    with get_db_read() as db:
        row = db.execute(
            "SELECT * FROM inbound_client_ips WHERE id = ?", (ip_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")
        return dict(row)


@router.get("/by-email/{email}", summary="Get client IPs by email", response_model=InboundClientIP)
def get_client_ip_by_email(email: str):
    with get_db_read() as db:
        row = db.execute(
            "SELECT * FROM inbound_client_ips WHERE client_email = ?", (email,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")
        return dict(row)
