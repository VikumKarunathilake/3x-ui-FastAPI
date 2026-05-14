from fastapi import APIRouter, HTTPException
from api.database import get_db_read, get_db_write
from api.models import UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", summary="List all users")
def list_users():
    with get_db_read() as db:
        rows = db.execute("SELECT id, username FROM users").fetchall()
        return [dict(r) for r in rows]


@router.get("/{user_id}", summary="Get user by ID")
def get_user(user_id: int):
    with get_db_read() as db:
        row = db.execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(row)


@router.post("/", status_code=201, summary="Create a new user")
def create_user(body: UserCreate):
    with get_db_write() as db:
        cur = db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (body.username, body.password),
        )
        return {"id": cur.lastrowid, "username": body.username}


@router.patch("/{user_id}", summary="Update user fields")
def update_user(user_id: int, body: UserUpdate):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    with get_db_write() as db:
        row = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        db.execute(
            f"UPDATE users SET {set_clause} WHERE id = ?",
            (*fields.values(), user_id),
        )
        return {"id": user_id, "updated": list(fields.keys())}


@router.delete("/{user_id}", summary="Delete a user")
def delete_user(user_id: int):
    with get_db_write() as db:
        row = db.execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return {"deleted": True, "id": user_id, "username": row["username"]}
