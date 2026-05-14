#!/usr/bin/env python3
"""
Log collector — reads /usr/local/x-ui/access.log every 1 minute,
processes only NEW lines (identified by timestamp), and writes
parsed entries into /etc/x-ui/client.db.

Old activity entries are deleted each cycle to keep the DB lean.

Run:  python3 -m api.collector          (from /etc/x-ui)
  or: nohup python3 -m api.collector &  (background daemon)
"""
import re
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.client_db import init_client_db, get_client_db_write, get_client_db_read

ACCESS_LOG = "/usr/local/x-ui/access.log"

# How long to keep activity entries (seconds). Default: 5 minutes.
ACTIVITY_RETENTION_SECONDS = 300

# Collector interval (seconds)
COLLECT_INTERVAL = 60

# Regex to parse a single xray access log line
_LINE_RE = re.compile(
    r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s+"  # timestamp
    r"from\s+(?:tcp:)?(\d+\.\d+\.\d+\.\d+):\d+\s+"      # source IP
    r"accepted\s+"
    r"(tcp|udp):"                                          # protocol
    r"(.+?)\s+"                                            # destination
    r"\[(.+?)\]\s+"                                        # route
    r"email:\s+(.+)$"                                      # email
)


def _parse_line(line: str) -> dict | None:
    m = _LINE_RE.match(line.strip())
    if not m:
        return None
    ts, source_ip, proto, dest, route, email = m.groups()
    return {
        "timestamp": ts,
        "source_ip": source_ip,
        "protocol": proto,
        "destination": f"{proto}:{dest}",
        "route": route.strip(),
        "email": email.strip(),
    }


def _get_last_timestamp() -> str:
    """Read the last processed timestamp from collector_state."""
    with get_client_db_read() as db:
        row = db.execute("SELECT last_timestamp FROM collector_state WHERE id = 1").fetchone()
        return row["last_timestamp"] if row else ""


def _set_last_timestamp(db, ts: str):
    """Update the last processed timestamp in collector_state."""
    db.execute("UPDATE collector_state SET last_timestamp = ? WHERE id = 1", (ts,))


def _get_or_create_client(db, email: str) -> int:
    row = db.execute("SELECT id FROM clients WHERE email = ?", (email,)).fetchone()
    if row:
        return row["id"]
    cur = db.execute("INSERT INTO clients (email) VALUES (?)", (email,))
    return cur.lastrowid


def _upsert_ip(db, client_id: int, ip: str, ts: str):
    existing = db.execute(
        "SELECT id FROM client_ips WHERE client_id = ? AND ip = ?",
        (client_id, ip),
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE client_ips SET last_seen = ?, hit_count = hit_count + 1 WHERE id = ?",
            (ts, existing["id"]),
        )
    else:
        db.execute(
            "INSERT INTO client_ips (client_id, ip, first_seen, last_seen) VALUES (?, ?, ?, ?)",
            (client_id, ip, ts, ts),
        )


def _insert_activity(db, client_id: int, entry: dict):
    db.execute(
        "INSERT INTO client_activity (client_id, timestamp, protocol, destination, route) "
        "VALUES (?, ?, ?, ?, ?)",
        (client_id, entry["timestamp"], entry["protocol"], entry["destination"], entry["route"]),
    )


def _delete_old_activity(db):
    """Delete activity entries older than ACTIVITY_RETENTION_SECONDS."""
    # xray timestamps are like "2026/05/14 12:54:02.676673"
    # We compare as strings since they're lexicographically sortable
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=ACTIVITY_RETENTION_SECONDS)
    cutoff_str = cutoff.strftime("%Y/%m/%d %H:%M:%S")
    deleted = db.execute("DELETE FROM client_activity WHERE timestamp < ?", (cutoff_str,))
    return deleted.rowcount


def collect_once():
    """Read new log lines since last timestamp, write to client.db, delete old activity."""
    last_ts = _get_last_timestamp()
    new_entries = []
    max_ts = last_ts

    with open(ACCESS_LOG, "r") as f:
        for line in f:
            entry = _parse_line(line)
            if not entry:
                continue
            # Only process lines with timestamp > last processed
            if entry["timestamp"] > last_ts:
                new_entries.append(entry)
                if entry["timestamp"] > max_ts:
                    max_ts = entry["timestamp"]

    if new_entries:
        with get_client_db_write() as db:
            for entry in new_entries:
                client_id = _get_or_create_client(db, entry["email"])
                _upsert_ip(db, client_id, entry["source_ip"], entry["timestamp"])
                _insert_activity(db, client_id, entry)
            _set_last_timestamp(db, max_ts)
            deleted = _delete_old_activity(db)
        print(f"[collector] Processed {len(new_entries)} new entries, deleted {deleted} old entries")
    else:
        # Still clean up old activity even if no new entries
        with get_client_db_write() as db:
            deleted = _delete_old_activity(db)
        if deleted:
            print(f"[collector] No new entries, deleted {deleted} old entries")


def run_daemon():
    """Run the collector every COLLECT_INTERVAL seconds."""
    print(f"[collector] Starting daemon (interval={COLLECT_INTERVAL}s, retention={ACTIVITY_RETENTION_SECONDS}s)")
    init_client_db()

    while True:
        try:
            collect_once()
        except Exception as e:
            print(f"[collector] Error: {e}")
        time.sleep(COLLECT_INTERVAL)


if __name__ == "__main__":
    run_daemon()
