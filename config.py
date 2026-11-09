from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    mode: str = os.getenv("APP_MODE", "demo").lower()
    mariadb_host: str = os.getenv("MARIADB_HOST", "127.0.0.1")
    mariadb_port: int = int(os.getenv("MARIADB_PORT", "3306"))
    mariadb_database: str = os.getenv("MARIADB_DATABASE", "shopsphere")
    mariadb_user: str = os.getenv("MARIADB_USER", "shopsphere")
    mariadb_password: str = os.getenv("MARIADB_PASSWORD", "")
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "shopsphere")
    sqlite_path: Path = Path(os.getenv("SQLITE_PATH", "data/shopsphere.db"))


settings = Settings()
