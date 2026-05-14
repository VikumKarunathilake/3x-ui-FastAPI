"""
client.db — Separate SQLite database that collects per-client activity
from the xray access log (/usr/local/x-ui/access.log).

Tables:
  clients              — unique client emails
  client_ips           — IPs seen per client (with first/last timestamps)
  client_activity      — connection log entries (protocol, dest, route, timestamp)
  collector_state      — tracks last processed log timestamp
  usage_YYYY_MM        — monthly tables for hourly traffic snapshots (partitioned)
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

CLIENT_DB_PATH = "/etc/x-ui/client.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS client_ips (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id   INTEGER NOT NULL,
    ip          TEXT NOT NULL,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    hit_count   INTEGER DEFAULT 1,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    UNIQUE(client_id, ip)
);

CREATE TABLE IF NOT EXISTS client_activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id   INTEGER NOT NULL,
    timestamp   TEXT NOT NULL,
    protocol    TEXT NOT NULL,
    destination TEXT NOT NULL,
    route       TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS collector_state (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    last_timestamp  TEXT NOT NULL DEFAULT ''
);

INSERT OR IGNORE INTO collector_state (id, last_timestamp) VALUES (1, '');

CREATE INDEX IF NOT EXISTS idx_activity_client    ON client_activity(client_id);
CREATE INDEX IF NOT EXISTS idx_activity_ts        ON client_activity(timestamp);
CREATE INDEX IF NOT EXISTS idx_client_ips_client  ON client_ips(client_id);
"""


def init_client_db():
    """Create the client.db file and core tables if they don't exist."""
    conn = sqlite3.connect(CLIENT_DB_PATH)
    conn.executescript(_SCHEMA)
    conn.close()


def _usage_table_name(year: int, month: int) -> str:
    """Return the table name for a given month: usage_2026_05"""
    return f"usage_{year:04d}_{month:02d}"


def get_current_usage_table() -> str:
    """Return the table name for the current month."""
    now = datetime.now(timezone.utc)
    return _usage_table_name(now.year, now.month)


def ensure_usage_table(db, table_name: str):
    """Create a monthly usage table if it doesn't exist."""
    db.executescript(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT NOT NULL,
            snapshot_ts TEXT NOT NULL,
            up          INTEGER NOT NULL DEFAULT 0,
            down        INTEGER NOT NULL DEFAULT 0,
            total_quota INTEGER NOT NULL DEFAULT 0,
            enable      INTEGER NOT NULL DEFAULT 1,
            UNIQUE(email, snapshot_ts)
        );
        CREATE INDEX IF NOT EXISTS idx_{table_name}_email ON {table_name}(email);
        CREATE INDEX IF NOT EXISTS idx_{table_name}_ts    ON {table_name}(snapshot_ts);
    """)


def list_usage_tables(db) -> list[str]:
    """Return all usage_YYYY_MM table names that exist, sorted."""
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'usage_%' ORDER BY name"
    ).fetchall()
    return [r["name"] if isinstance(r, sqlite3.Row) else r[0] for r in rows]


def cleanup_old_usage_tables(db, keep_months: int = 1):
    """Drop usage tables older than keep_months (relative to current month).
    With keep_months=1, keeps current month + previous month."""
    now = datetime.now(timezone.utc)
    # Build set of table names to keep
    keep = set()
    for offset in range(keep_months + 1):
        m = now.month - offset
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        keep.add(_usage_table_name(y, m))

    for table in list_usage_tables(db):
        if table not in keep:
            db.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"[cleanup] Dropped old table: {table}")


def migrate_old_usage_table(db):
    """Migrate data from the old single client_usage table into monthly tables,
    then drop the old table. Safe to call multiple times."""
    old = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='client_usage'"
    ).fetchone()
    if not old:
        return 0

    rows = db.execute("SELECT * FROM client_usage").fetchall()
    if not rows:
        db.execute("DROP TABLE client_usage")
        return 0

    count = 0
    for row in rows:
        ts = row["snapshot_ts"]
        try:
            year = int(ts[:4])
            month = int(ts[5:7])
        except (ValueError, IndexError):
            continue
        table = _usage_table_name(year, month)
        ensure_usage_table(db, table)
        db.execute(
            f"""INSERT OR IGNORE INTO {table}
                (email, snapshot_ts, up, down, total_quota, enable)
                VALUES (?, ?, ?, ?, ?, ?)""",
            (row["email"], row["snapshot_ts"], row["up"], row["down"],
             row["total_quota"], row["enable"]),
        )
        count += 1

    db.execute("DROP TABLE client_usage")
    print(f"[migrate] Moved {count} rows from client_usage → monthly tables")
    return count


def _make_client_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(
        CLIENT_DB_PATH,
        check_same_thread=False,
        timeout=3,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=3000;")
    return conn


@contextmanager
def get_client_db_read():
    conn = _make_client_connection()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_client_db_write():
    conn = _make_client_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
