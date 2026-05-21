import re
import os
import aiosqlite
import logging
from pathlib import Path
from datetime import datetime
from api.config import settings
from api.database import get_client_by_email

logger = logging.getLogger(__name__)

LOG_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.?\d*) "
    r"(?:from )?(?P<client_address>(?:(?:tcp|udp):)?[\d\.:]+) "
    r"accepted "
    r"(?P<protocol>tcp|udp):(?P<destination>[\d\.:]+) "
    r"\[(?P<inbound>[^ ]+) >> (?P<outbound>[^\]]+)\] "
    r"email: (?P<email>.*)"
)


async def collect_logs():
    """Read new lines from access.log and insert into traffic.db"""
    log_path = Path(os.getenv("ACCESS_LOG_PATH", "/usr/local/x-ui/access.log"))
    if not log_path.is_absolute():
        log_path = settings.BASE_DIR / log_path.as_posix().lstrip("/")

    if not log_path.exists():
        logger.warning(f"Access log not found at {log_path}")
        return

    db_path = settings.full_traffic_db_path

    state_file = db_path.parent / "collector_state.txt"
    last_pos = 0
    if state_file.exists():
        try:
            last_pos = int(state_file.read_text())
        except Exception:
            last_pos = 0

    file_size = log_path.stat().st_size
    if file_size < last_pos:
        # Log rotated
        last_pos = 0

    if file_size == last_pos:
        return

    new_logs = []
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(last_pos)
            lines = f.readlines()
            last_pos = f.tell()

            for line in lines:
                match = LOG_PATTERN.search(line)
                if match:
                    data = match.groupdict()
                    email = data["email"].strip()
                    client_id = None
                    client_info = await get_client_by_email(email)
                    if client_info:
                        client_id = client_info.get("id")

                    raw_addr = data["client_address"]
                    ip = raw_addr.split(":")[-2] if ":" in raw_addr else raw_addr
                    if "]" in ip:
                        ip = ip.split("]")[-1]
                    ip = ip.split(":")[-1]
                    parts = raw_addr.split(":")
                    if len(parts) >= 2:
                        ip = parts[-2]
                    else:
                        ip = raw_addr

                    raw_ts = data["timestamp"]
                    try:
                        # Split fractional seconds to handle various formats robustly
                        dt = datetime.strptime(
                            raw_ts.split(".")[0], "%Y/%m/%d %H:%M:%S"
                        )
                        unix_ts = int(dt.timestamp())
                    except Exception as e:
                        logger.error(f"Error parsing log timestamp {raw_ts}: {e}")
                        unix_ts = raw_ts

                    new_logs.append(
                        {
                            "client_id": client_id,
                            "email": email,
                            "ip": ip,
                            "last_seen": unix_ts,
                        }
                    )

        if new_logs:
            async with aiosqlite.connect(db_path) as db:
                await db.executemany(
                    """
                    INSERT OR REPLACE INTO client_ips (client_id, email, ip, last_seen)
                    VALUES (:client_id, :email, :ip, :last_seen)
                    """,
                    new_logs,
                )
                await db.commit()
            logger.info(f"Updated IP records for {len(new_logs)} connections")
            try:
                with open(log_path, "w"):
                    pass
                state_file.write_text("0")
                logger.info(f"Cleared log file {log_path}")
            except Exception as e:
                logger.error(f"Failed to clear log file: {e}")
        else:
            state_file.write_text(str(last_pos))
    except Exception as e:
        logger.error(f"Error collecting logs: {e}")


async def collect_traffic_snapshots():
    """Query client_traffics from x-ui.db and insert snapshots into traffic.db"""
    import time
    from api.database import get_db

    db_path = settings.full_traffic_db_path
    clients = []

    try:
        async with get_db() as db:
            async with db.execute(
                "SELECT id, email, up, down FROM client_traffics WHERE email IS NOT NULL AND email != ''"
            ) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    clients.append(dict(row))
    except Exception as e:
        logger.error(f"Error querying client_traffics from x-ui.db: {e}")
        return

    if not clients:
        logger.info("No clients found to snapshot traffic.")
        return

    now = int(time.time())
    snapshot_records = [
        {
            "client_id": client["id"],
            "email": client["email"],
            "up": client["up"],
            "down": client["down"],
            "timestamp": now,
        }
        for client in clients
    ]

    try:
        async with aiosqlite.connect(db_path) as db:
            await db.executemany(
                """
                INSERT INTO client_traffic_snapshots (client_id, email, up, down, timestamp)
                VALUES (:client_id, :email, :up, :down, :timestamp)
                """,
                snapshot_records,
            )
            await db.commit()
        logger.info(f"Saved {len(snapshot_records)} client traffic snapshots at {now}")
    except Exception as e:
        logger.error(f"Error saving traffic snapshots to traffic.db: {e}")


async def get_traffic_aggregation(email: str):
    """
    Fetch all historical snapshots for an email from traffic.db,
    calculate deltas between consecutive points (handling resets),
    and aggregate them by Day, Week, and Month.
    """
    from datetime import timezone, timedelta

    db_path = settings.full_traffic_db_path
    snapshots = []

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT up, down, timestamp FROM client_traffic_snapshots WHERE email = ? ORDER BY timestamp ASC",
                (email,),
            ) as cursor:
                rows = await cursor.fetchall()
                snapshots = [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error querying client_traffic_snapshots: {e}")
        return {"email": email, "daily": [], "weekly": [], "monthly": []}

    daily_map = {}
    weekly_map = {}
    monthly_map = {}

    if len(snapshots) >= 1:
        for i in range(len(snapshots)):
            snapshot = snapshots[i]
            if i == 0:
                # First snapshot, treat its values as initial delta from 0
                delta_up = snapshot["up"]
                delta_down = snapshot["down"]
            else:
                prev = snapshots[i - 1]
                delta_up = snapshot["up"] - prev["up"]
                delta_down = snapshot["down"] - prev["down"]
                if delta_up < 0:
                    delta_up = snapshot["up"]
                if delta_down < 0:
                    delta_down = snapshot["down"]

            dt = datetime.fromtimestamp(snapshot["timestamp"], tz=timezone.utc)

            # Daily grouping
            day_str = dt.strftime("%Y-%m-%d")
            if day_str not in daily_map:
                daily_map[day_str] = {"up": 0, "down": 0}
            daily_map[day_str]["up"] += delta_up
            daily_map[day_str]["down"] += delta_down

            # Weekly grouping (Group by Monday of that week)
            monday = dt - timedelta(days=dt.weekday())
            week_str = monday.strftime("%Y-%m-%d")
            if week_str not in weekly_map:
                weekly_map[week_str] = {"up": 0, "down": 0}
            weekly_map[week_str]["up"] += delta_up
            weekly_map[week_str]["down"] += delta_down

            # Monthly grouping
            month_str = dt.strftime("%Y-%m")
            if month_str not in monthly_map:
                monthly_map[month_str] = {"up": 0, "down": 0}
            monthly_map[month_str]["up"] += delta_up
            monthly_map[month_str]["down"] += delta_down

    daily = sorted(
        [
            {
                "label": k,
                "up": v["up"],
                "down": v["down"],
                "total": v["up"] + v["down"],
            }
            for k, v in daily_map.items()
        ],
        key=lambda x: x["label"],
    )

    weekly = sorted(
        [
            {
                "label": k,
                "up": v["up"],
                "down": v["down"],
                "total": v["up"] + v["down"],
            }
            for k, v in weekly_map.items()
        ],
        key=lambda x: x["label"],
    )

    monthly = sorted(
        [
            {
                "label": k,
                "up": v["up"],
                "down": v["down"],
                "total": v["up"] + v["down"],
            }
            for k, v in monthly_map.items()
        ],
        key=lambda x: x["label"],
    )

    return {
        "email": email,
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
    }
