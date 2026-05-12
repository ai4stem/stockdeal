from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingMode(str, Enum):
    OFF = "OFF"
    SIMULATION = "SIMULATION"
    CONFIRM = "CONFIRM"
    AUTO = "AUTO"


class KISEnv(str, Enum):
    PROD = "prod"
    PAPER = "paper"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "dev"
    tz: str = "Asia/Seoul"
    log_level: str = "INFO"
    daily_report_hour: int = 22
    trading_mode: TradingMode = TradingMode.SIMULATION

    # KIS
    kis_app_key: SecretStr = SecretStr("")
    kis_app_secret: SecretStr = SecretStr("")
    kis_account_no: str = ""
    kis_account_product_code: str = "01"
    kis_env: KISEnv = KISEnv.PROD

    # Anthropic
    anthropic_api_key: SecretStr = SecretStr("")
    claude_model_fast: str = "claude-haiku-4-5-20251001"
    claude_model_smart: str = "claude-sonnet-4-6"
    claude_model_deep: str = "claude-opus-4-7"

    # DART
    dart_api_key: SecretStr = SecretStr("")

    # News
    finnhub_api_key: SecretStr = SecretStr("")
    naver_client_id: str = ""
    naver_client_secret: SecretStr = SecretStr("")

    # Telegram
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: str = ""

    # Kakao
    kakao_rest_api_key: SecretStr = SecretStr("")
    kakao_refresh_token: SecretStr = SecretStr("")

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    from_email: str = ""
    to_email: str = ""

    # DB
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "stockdeal"
    db_password: SecretStr = SecretStr("")
    db_database: str = "stockdeal"

    # Watchlist
    watchlist: str = "403870,005930,000660,222800,005290,442900"
    primary_ticker: str = "403870"

    # Risk
    daily_order_budget_ratio: float = 0.05
    max_position_ratio: float = 0.20
    order_confirm_timeout_sec: int = 600

    @computed_field
    @property
    def watchlist_tickers(self) -> list[str]:
        return [t.strip() for t in self.watchlist.split(",") if t.strip()]

    @computed_field
    @property
    def db_url(self) -> str:
        pw = self.db_password.get_secret_value()
        return (
            f"mysql+pymysql://{self.db_user}:{pw}"
            f"@{self.db_host}:{self.db_port}/{self.db_database}?charset=utf8mb4"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
