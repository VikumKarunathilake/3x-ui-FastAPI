import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    BASE_DIR = Path(__file__).parent.parent
    XUI_DB_PATH: str = os.getenv("XUI_DB_PATH", "/etc/x-ui/x-ui.db")

    @property
    def full_db_path(self) -> Path:
        local_path = self.BASE_DIR / self.XUI_DB_PATH.lstrip("/")
        if local_path.exists():
            return local_path
        return Path(self.XUI_DB_PATH)


settings = Settings()
