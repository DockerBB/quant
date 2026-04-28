"""Global configuration via environment variables and settings.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Project paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    CONFIG_DIR: Path = PROJECT_ROOT / "config"

    # Data source selection
    PRIMARY_SOURCE: str = "akshare"       # akshare | baostock
    FALLBACK_SOURCE: str = "baostock"     # baostock | none

    # Database
    SQLITE_PATH: Path = DATA_DIR / "quant.db"

    # Storage paths
    DAILY_DIR: Path = DATA_DIR / "parquet" / "daily"
    FINANCIAL_DIR: Path = DATA_DIR / "financial"

    # Data quality
    MAX_MISSING_PCT: float = 0.20         # max missing rate per stock
    WINSORIZE_PCT: Tuple[float, float] = (1.0, 99.0)

    # Stock universe defaults
    EXCLUDE_ST: bool = True
    EXCLUDE_NEW_STOCK_DAYS: int = 60
    MIN_LISTING_DAYS: int = 120

    # Scheduler
    DATA_REFRESH_HOUR: int = 15
    DATA_REFRESH_MINUTE: int = 30

    # API
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_prefix = "QUANT_"
        extra = "allow"

    @classmethod
    def from_yaml(cls) -> "Settings":
        yaml_path = Path(__file__).resolve().parent.parent.parent.parent / "config" / "settings.yaml"
        values: dict = {}
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    values = loaded
        return cls(**values)

    def ensure_dirs(self) -> None:
        for path in [self.DATA_DIR, self.DAILY_DIR, self.FINANCIAL_DIR]:
            path.mkdir(parents=True, exist_ok=True)


settings = Settings.from_yaml()
settings.ensure_dirs()
