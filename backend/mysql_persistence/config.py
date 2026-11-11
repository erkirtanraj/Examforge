"""Validated MySQL configuration; never falls back to MongoDB settings."""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Mapping
from sqlalchemy.engine import URL, make_url

class MySQLConfigurationError(ValueError):
    """Raised when MySQL configuration is missing or unsafe."""

@dataclass(frozen=True, repr=False)
class MySQLSettings:
    url: URL
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800

    @property
    def database_name(self) -> str:
        return self.url.database or ""

    def safe_url(self) -> str:
        return self.url.render_as_string(hide_password=True)

    def __repr__(self) -> str:
        return (f"MySQLSettings(url={self.safe_url()!r}, pool_size={self.pool_size!r}, "
                f"max_overflow={self.max_overflow!r}, pool_timeout={self.pool_timeout!r}, "
                f"pool_recycle={self.pool_recycle!r})")

def _positive_int(env: Mapping[str, str], key: str, default: int) -> int:
    try:
        value = int(env.get(key, str(default)))
    except (TypeError, ValueError) as exc:
        raise MySQLConfigurationError(f"{key} must be an integer") from exc
    if value <= 0:
        raise MySQLConfigurationError(f"{key} must be greater than zero")
    return value

def load_mysql_settings(env: Mapping[str, str] | None = None) -> MySQLSettings:
    """Load mysql+asyncmy from DATABASE_URL or MYSQL_* variables."""
    source = os.environ if env is None else env
    raw_url = (source.get("DATABASE_URL") or "").strip()
    if raw_url:
        try:
            url = make_url(raw_url)
        except Exception as exc:
            raise MySQLConfigurationError("DATABASE_URL is not a valid SQLAlchemy URL") from exc
    else:
        required = ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
        missing = [key for key in required if not source.get(key)]
        if missing:
            raise MySQLConfigurationError("Missing MySQL configuration: " + ", ".join(missing))
        try:
            port = int(source.get("MYSQL_PORT", "3306"))
        except ValueError as exc:
            raise MySQLConfigurationError("MYSQL_PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise MySQLConfigurationError("MYSQL_PORT must be between 1 and 65535")
        url = URL.create(
            "mysql+asyncmy", username=source["MYSQL_USER"], password=source["MYSQL_PASSWORD"],
            host=source["MYSQL_HOST"], port=port, database=source["MYSQL_DATABASE"],
            query={"charset": "utf8mb4"},
        )
    if url.drivername != "mysql+asyncmy":
        raise MySQLConfigurationError("DATABASE_URL must use the mysql+asyncmy driver; SQLite and sync drivers are not supported")
    if not url.host or not url.database or not url.username:
        raise MySQLConfigurationError("DATABASE_URL must include host, username and database")
    return MySQLSettings(
        url=url,
        pool_size=_positive_int(source, "MYSQL_POOL_SIZE", 5),
        max_overflow=_positive_int(source, "MYSQL_MAX_OVERFLOW", 10),
        pool_timeout=_positive_int(source, "MYSQL_POOL_TIMEOUT", 30),
        pool_recycle=_positive_int(source, "MYSQL_POOL_RECYCLE", 1800),
    )

def require_approved_test_database(settings: MySQLSettings) -> None:
    """Fail closed before destructive test setup unless DB is examforge_test."""
    if settings.database_name != "examforge_test":
        raise MySQLConfigurationError("Refusing destructive test setup: database must be exactly 'examforge_test'")
