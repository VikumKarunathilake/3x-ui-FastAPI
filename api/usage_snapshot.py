#!/usr/bin/env python3
"""
Usage snapshot — reads current traffic counters from x-ui.db (client_traffics)
and saves a timestamped snapshot into client.db monthly table (usage_YYYY_MM).

Designed to run via cron every hour:
  0 * * * * cd /etc/x-ui && python3 -m api.usage_snapshot

Each snapshot records the raw up/down byte counters at that hour.
Daily usage = difference between the last snapshot of the day and the first.
Only keeps 1 month of history — old monthly tables are automatically dropped.
"""
import os
import sys
import sqlite3
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.client_db import (
    init_client_db, get_client_db_write,
    get_current_usage_table, ensure_usage_table,
    cleanup_old_usage_tables, migrate_old_usage_table,
)

XUI_DB_PATH = "/etc/x-ui/x-ui.db"


def snapshot_usage(force: bool = False):
    """Read all client_traffics from x-ui.db and save a snapshot into client.db."""
    now = datetime.now(timezone.utc)

    # Only run at the top of the hour (minute 0-2 to allow for cron delay)
    if not force and now.minute > 2:
        print(f"[usage] Skipped — current time is {now.strftime('%H:%M')}, "
              f"only runs at HH:00. Use --force to override.")
        return

    init_client_db()

    # Current month's table
    table = get_current_usage_table()
    snapshot_ts = now.strftime("%Y-%m-%d %H:00")

    # Read current traffic from x-ui.db
    xui_conn = sqlite3.connect(XUI_DB_PATH, timeout=5)
    xui_conn.row_factory = sqlite3.Row
    xui_conn.execute("PRAGMA busy_timeout=5000;")

    rows = xui_conn.execute(
        "SELECT email, up, down, total, enable FROM client_traffics"
    ).fetchall()
    xui_conn.close()

    if not rows:
        print("[usage] No client_traffics found in x-ui.db")
        return

    # Write snapshots into monthly table
    count = 0
    with get_client_db_write() as db:
        # Migrate old single-table data if it exists
        migrate_old_usage_table(db)

        # Ensure this month's table exists
        ensure_usage_table(db, table)

        for row in rows:
            db.execute(
                f"""INSERT OR REPLACE INTO {table}
                   (email, snapshot_ts, up, down, total_quota, enable)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (row["email"], snapshot_ts, row["up"], row["down"],
                 row["total"], row["enable"]),
            )
            count += 1

        # Drop tables older than 1 month
        cleanup_old_usage_tables(db, keep_months=1)

    print(f"[usage] Saved {count} snapshots → {table} at {snapshot_ts}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Snapshot client traffic usage")
    parser.add_argument("--force", action="store_true",
                        help="Run even if current time is not at the top of the hour")
    args = parser.parse_args()
    snapshot_usage(force=args.force)
