import sqlite3
from contextlib import contextmanager

DB_PATH = "/etc/x-ui/x-ui.db"

# ── Busy timeout (ms) ─────────────────────────────────────────────
# 3x-ui writes to this DB every ~1s. A generous timeout prevents
# SQLITE_BUSY errors when our write overlaps with theirs.
_BUSY_TIMEOUT_MS = 3000


def _make_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        timeout=_BUSY_TIMEOUT_MS / 1000,  # sqlite3 uses seconds
    )
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS};")
    return conn


@contextmanager
def get_db_read():
    """Read-only context — no commit, short-lived connection."""
    conn = _make_connection()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_db_write():
    """Write context — commits on success, rolls back on error."""
    conn = _make_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Backwards compat alias (used by existing code during migration) ──
get_db = get_db_write
