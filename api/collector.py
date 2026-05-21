import re
import os
import aiosqlite
import logging
from pathlib import Path
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

                    new_logs.append(
                        {
                            "client_id": client_id,
                            "email": email,
                            "ip": ip,
                            "last_seen": data["timestamp"],
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
