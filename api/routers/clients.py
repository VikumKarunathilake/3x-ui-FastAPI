from fastapi import APIRouter, HTTPException, Query
from api.client_db import (
    get_client_db_read, list_usage_tables,
    get_current_usage_table, _usage_table_name,
)
from api.models import (
    ClientDetail, ClientIP, ClientActivityEntry, ClientSummary,
    UsageSnapshot, DailyUsage, MonthlyUsageSummary,
)

router = APIRouter(prefix="/clients", tags=["Clients (Activity Log)"])


@router.get("/", summary="List all tracked clients", response_model=list[ClientSummary])
def list_clients():
    """List all clients that have been seen in the access log."""
    with get_client_db_read() as db:
        rows = db.execute("""
            SELECT c.id, c.email,
                   COUNT(DISTINCT ci.ip) AS ip_count,
                   COUNT(ca.id) AS activity_count
            FROM clients c
            LEFT JOIN client_ips ci ON ci.client_id = c.id
            LEFT JOIN client_activity ca ON ca.client_id = c.id
            GROUP BY c.id
            ORDER BY c.email
        """).fetchall()
        return [dict(r) for r in rows]


@router.get("/{client_id}", summary="Get client details", response_model=ClientDetail)
def get_client(client_id: int):
    """Get a client's email, connected IPs, and recent activity."""
    with get_client_db_read() as db:
        client = db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        ips = db.execute(
            "SELECT * FROM client_ips WHERE client_id = ? ORDER BY last_seen DESC",
            (client_id,),
        ).fetchall()

        activities = db.execute(
            "SELECT * FROM client_activity WHERE client_id = ? ORDER BY timestamp DESC LIMIT 100",
            (client_id,),
        ).fetchall()

        return {
            "id": client["id"],
            "email": client["email"],
            "ips": [dict(r) for r in ips],
            "recent_activity": [dict(r) for r in activities],
        }


@router.get("/by-email/{email}", summary="Get client by email", response_model=ClientDetail)
def get_client_by_email(email: str):
    """Get a client's details by their email address."""
    with get_client_db_read() as db:
        client = db.execute("SELECT * FROM clients WHERE email = ?", (email,)).fetchone()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        ips = db.execute(
            "SELECT * FROM client_ips WHERE client_id = ? ORDER BY last_seen DESC",
            (client["id"],),
        ).fetchall()

        activities = db.execute(
            "SELECT * FROM client_activity WHERE client_id = ? ORDER BY timestamp DESC LIMIT 100",
            (client["id"],),
        ).fetchall()

        return {
            "id": client["id"],
            "email": client["email"],
            "ips": [dict(r) for r in ips],
            "recent_activity": [dict(r) for r in activities],
        }


@router.get("/{client_id}/ips", summary="Get client IPs", response_model=list[ClientIP])
def get_client_ips(client_id: int):
    """Get all IPs seen for a specific client."""
    with get_client_db_read() as db:
        client = db.execute("SELECT id FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        rows = db.execute(
            "SELECT * FROM client_ips WHERE client_id = ? ORDER BY last_seen DESC",
            (client_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/{client_id}/activity", summary="Get client activity", response_model=list[ClientActivityEntry])
def get_client_activity(
    client_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Get connection activity for a specific client."""
    with get_client_db_read() as db:
        client = db.execute("SELECT id FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        rows = db.execute(
            "SELECT * FROM client_activity WHERE client_id = ? ORDER BY timestamp DESC LIMIT ?",
            (client_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Usage (Monthly Tables) ────────────────────────────────────────

def _resolve_table(month: str | None) -> str:
    """Resolve month param (YYYY-MM) to table name. Defaults to current month."""
    if month:
        try:
            year, m = int(month[:4]), int(month[5:7])
            return _usage_table_name(year, m)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
    return get_current_usage_table()


def _table_exists(db, table: str) -> bool:
    row = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


@router.get("/usage/months", summary="List available usage months")
def list_months():
    """List all months that have usage data (one table per month)."""
    with get_client_db_read() as db:
        tables = list_usage_tables(db)
        months = []
        for t in tables:
            parts = t.replace("usage_", "").split("_")
            if len(parts) == 2:
                months.append(f"{parts[0]}-{parts[1]}")
        return {"months": months}


@router.get("/usage/snapshots", summary="List usage snapshots", response_model=list[UsageSnapshot])
def list_usage_snapshots(
    month: str = Query(default=None, description="Month (YYYY-MM). Defaults to current."),
    email: str = Query(default=None, description="Filter by email"),
    date: str = Query(default=None, description="Filter by date (YYYY-MM-DD)"),
):
    """List hourly traffic snapshots from a specific month's table."""
    table = _resolve_table(month)
    with get_client_db_read() as db:
        if not _table_exists(db, table):
            return []
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = []
        if email:
            query += " AND email = ?"
            params.append(email)
        if date:
            query += " AND snapshot_ts LIKE ?"
            params.append(f"{date}%")
        query += " ORDER BY snapshot_ts DESC, email"
        rows = db.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.get("/usage/daily", summary="Get daily usage per client", response_model=list[DailyUsage])
def get_daily_usage(
    date: str = Query(default=None, description="Date (YYYY-MM-DD). Defaults to today."),
):
    """Calculate daily usage by comparing first and last snapshots of the day."""
    if not date:
        from datetime import datetime, timezone
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        year, month_num = int(date[:4]), int(date[5:7])
        table = _usage_table_name(year, month_num)
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    with get_client_db_read() as db:
        if not _table_exists(db, table):
            return []
        rows = db.execute(f"""
            SELECT
                email,
                ? AS date,
                MAX(up) - MIN(up) AS up_used,
                MAX(down) - MIN(down) AS down_used,
                (MAX(up) - MIN(up)) + (MAX(down) - MIN(down)) AS total_used
            FROM {table}
            WHERE snapshot_ts LIKE ?
            GROUP BY email
            HAVING COUNT(*) >= 1
            ORDER BY total_used DESC
        """, (date, f"{date}%")).fetchall()
        return [dict(r) for r in rows]


@router.get("/usage/monthly", summary="Get monthly usage summary", response_model=list[MonthlyUsageSummary])
def get_monthly_usage(
    month: str = Query(default=None, description="Month (YYYY-MM). Defaults to current."),
):
    """Calculate total usage for the entire month per client."""
    table = _resolve_table(month)
    if not month:
        from datetime import datetime, timezone
        month = datetime.now(timezone.utc).strftime("%Y-%m")

    with get_client_db_read() as db:
        if not _table_exists(db, table):
            return []
        rows = db.execute(f"""
            SELECT
                email,
                ? AS month,
                MAX(up) - MIN(up) AS up_used,
                MAX(down) - MIN(down) AS down_used,
                (MAX(up) - MIN(up)) + (MAX(down) - MIN(down)) AS total_used,
                COUNT(*) AS snapshot_count
            FROM {table}
            GROUP BY email
            ORDER BY total_used DESC
        """, (month,)).fetchall()
        return [dict(r) for r in rows]


@router.get("/usage/by-email/{email}", summary="Get usage history for a client", response_model=list[UsageSnapshot])
def get_usage_by_email(
    email: str,
    month: str = Query(default=None, description="Month (YYYY-MM). Defaults to current."),
):
    """Get all hourly snapshots for a specific client email."""
    table = _resolve_table(month)
    with get_client_db_read() as db:
        if not _table_exists(db, table):
            raise HTTPException(status_code=404, detail="No usage data for this month")
        rows = db.execute(
            f"SELECT * FROM {table} WHERE email = ? ORDER BY snapshot_ts DESC",
            (email,),
        ).fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No usage data found for this email")
        return [dict(r) for r in rows]
