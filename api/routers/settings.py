from fastapi import APIRouter, HTTPException
from api.database import get_db_read, get_db_write
from api.models import SettingCreate, SettingUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/", summary="List all settings")
def list_settings():
    with get_db_read() as db:
        rows = db.execute("SELECT id, key, value FROM settings").fetchall()
        return [dict(r) for r in rows]


@router.get("/{setting_id}", summary="Get setting by ID")
def get_setting(setting_id: int):
    with get_db_read() as db:
        row = db.execute(
            "SELECT id, key, value FROM settings WHERE id = ?", (setting_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Setting not found")
        return dict(row)


@router.get("/by-key/{key}", summary="Get setting by key")
def get_setting_by_key(key: str):
    with get_db_read() as db:
        row = db.execute(
            "SELECT id, key, value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Setting not found")
        return dict(row)


@router.post("/", status_code=201, summary="Create a new setting")
def create_setting(body: SettingCreate):
    with get_db_write() as db:
        try:
            cur = db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                (body.key, body.value),
            )
            return {"id": cur.lastrowid, "key": body.key, "value": body.value}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{setting_id}", summary="Update setting value")
def update_setting(setting_id: int, body: SettingUpdate):
    with get_db_write() as db:
        row = db.execute(
            "SELECT id FROM settings WHERE id = ?", (setting_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Setting not found")
        db.execute(
            "UPDATE settings SET value = ? WHERE id = ?",
            (body.value, setting_id),
        )
        return {"id": setting_id, "value": body.value}


@router.delete("/{setting_id}", summary="Delete a setting")
def delete_setting(setting_id: int):
    with get_db_write() as db:
        row = db.execute(
            "SELECT id, key FROM settings WHERE id = ?", (setting_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Setting not found")
        db.execute("DELETE FROM settings WHERE id = ?", (setting_id,))
        return {"deleted": True, "id": setting_id, "key": row["key"]}
