from pydantic import Field, field_validator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings; provider secrets are excluded from representations/logs."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    database_url: str = Field(default="sqlite:///./investiq.db", validation_alias="DATABASE_URL")
    investiq_access_password: str | None = Field(default=None, repr=False, validation_alias="INVESTIQ_ACCESS_PASSWORD")
    nvidia_api_key: str | None = Field(default=None, repr=False, validation_alias="NVIDIA_API_KEY")
    nvidia_model: str = Field(default="nvidia/nemotron-3.5-lightning-30b-a3b", validation_alias="NVIDIA_MODEL")
    nvidia_timeout_seconds: float = Field(default=25.0, gt=0, le=120, validation_alias="NVIDIA_TIMEOUT_SECONDS")
    nvidia_max_tokens: int = Field(default=700, ge=64, le=4096, validation_alias="NVIDIA_MAX_TOKENS")
    http_timeout_seconds: float = Field(default=8.0, gt=0, le=60, validation_alias="HTTP_TIMEOUT_SECONDS")
    twelve_data_api_key: str | None = Field(default=None, repr=False, validation_alias="TWELVE_DATA_API_KEY")
    marketaux_api_key: str | None = Field(default=None, repr=False, validation_alias="MARKETAUX_API_KEY")
    fmp_api_key: str | None = Field(default=None, repr=False, validation_alias="FMP_API_KEY")
    sector_etf_fallback_enabled: bool = Field(default=True, validation_alias="INVESTIQ_SECTOR_ETF_FALLBACK_ENABLED")
    market_timezone: str = Field(default="America/Bogota", validation_alias="MARKET_TIMEZONE")
    headlines_cache_minutes: int = Field(default=15, ge=1, le=60)
    sec_user_agent: str = Field(default="", validation_alias="SEC_USER_AGENT")
    price_cache_minutes: int = Field(default=15, ge=1, le=60)
    news_cache_hours: int = Field(default=6, ge=1, le=12)
    filing_cache_hours: int = Field(default=24, ge=1, le=168)
    query_log_retention_days: int = Field(default=90, ge=1, le=3650)
    conversation_memory_days: int = Field(default=90, ge=1, le=365)
    show_diagnostics: bool = Field(default=False, validation_alias="INVESTIQ_SHOW_DIAGNOSTICS")
    log_level: str = Field(default="INFO", validation_alias="INVESTIQ_LOG_LEVEL")

    @property
    def has_nvidia_key(self) -> bool:
        return bool(self.nvidia_api_key and self.nvidia_api_key.strip())

    @property
    def has_twelve_data_key(self) -> bool:
        return bool(self.twelve_data_api_key and self.twelve_data_api_key.strip())

    @property
    def has_marketaux_key(self) -> bool:
        return bool(self.marketaux_api_key and self.marketaux_api_key.strip())

    @property
    def has_fmp_key(self) -> bool:
        return bool(self.fmp_api_key and self.fmp_api_key.strip())

    @field_validator("market_timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("MARKET_TIMEZONE debe ser una zona IANA válida") from None
        return value

    @field_validator("log_level")
    @classmethod
    def valid_log_level(cls, value):
        import logging

        level = value.upper().strip()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("INVESTIQ_LOG_LEVEL debe ser DEBUG, INFO, WARNING, ERROR o CRITICAL")
        return level


def get_settings() -> Settings:
    return Settings()
