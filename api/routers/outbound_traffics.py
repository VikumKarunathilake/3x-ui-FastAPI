from fastapi import APIRouter
from api.database import get_db_read
from api.models import OutboundTraffic

router = APIRouter(prefix="/outbound-traffics", tags=["Outbound Traffics"])

# ── READ-ONLY ──────────────────────────────────────────────────────
# Outbound traffic stats are entirely managed by 3x-ui.
# This API only exposes GET endpoints for monitoring.
# ───────────────────────────────────────────────────────────────────


@router.get("/", summary="List all outbound traffics", response_model=list[OutboundTraffic])
def list_outbound_traffics():
    with get_db_read() as db:
        rows = db.execute("SELECT * FROM outbound_traffics").fetchall()
        return [dict(r) for r in rows]


@router.get("/{traffic_id}", summary="Get outbound traffic by ID", response_model=OutboundTraffic)
def get_outbound_traffic(traffic_id: int):
    from fastapi import HTTPException
    with get_db_read() as db:
        row = db.execute(
            "SELECT * FROM outbound_traffics WHERE id = ?", (traffic_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Outbound traffic not found")
        return dict(row)


@router.get("/by-tag/{tag}", summary="Get outbound traffic by tag", response_model=OutboundTraffic)
def get_outbound_traffic_by_tag(tag: str):
    from fastapi import HTTPException
    with get_db_read() as db:
        row = db.execute(
            "SELECT * FROM outbound_traffics WHERE tag = ?", (tag,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Outbound traffic not found")
        return dict(row)
