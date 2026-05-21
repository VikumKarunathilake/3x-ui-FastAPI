import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    BASE_DIR = Path(__file__).parent.parent
    XUI_DB_PATH: str = os.getenv("XUI_DB_PATH", "/etc/x-ui/x-ui.db")
    TRAFFIC_DB_PATH: str = os.getenv("TRAFFIC_DB_PATH", "/etc/x-ui/traffic.db")

    @property
    def full_db_path(self) -> Path:
        local_path = self.BASE_DIR / self.XUI_DB_PATH.lstrip("/")
        if local_path.exists():
            return local_path
        return Path(self.XUI_DB_PATH)

    @property
    def full_traffic_db_path(self) -> Path:
        local_path = self.BASE_DIR / self.TRAFFIC_DB_PATH.lstrip("/")
        if local_path.exists():
            return local_path

        path = Path(self.TRAFFIC_DB_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "60"))
    COLLECT_INTERVAL: int = int(os.getenv("COLLECT_INTERVAL", "60"))
    TRAFFIC_SNAPSHOT_INTERVAL: int = int(os.getenv("TRAFFIC_SNAPSHOT_INTERVAL", "600"))

    @property
    def allow_origins(self) -> List[str]:
        origins = os.getenv("ALLOW_ORIGINS", "")
        if not origins:
            return ["http://localhost:4321", "https://consol.ceyloncloud.site"]
        return [origin.strip() for origin in origins.split(",") if origin.strip()]


settings = Settings()

