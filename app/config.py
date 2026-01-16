from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    database_url: str
    log_level: str
    pronunciation_enabled: bool = False
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    translation_enabled: bool = True
    google_translate_api_key: str | None = None
    google_translate_url: str = "https://translation.googleapis.com/language/translate/v2"
    google_translate_timeout_seconds: int = 15
    admin_user_ids: set[int] = set()
    backup_dir: str = "/app/backups"
    db_backup_dir: str = "/backups"
    auto_backup_enabled: bool = True
    auto_backup_schedule: str = "daily"
    auto_backup_hour: int = 2
    auto_backup_minute: int = 0
    auto_backup_retention_days: int = 14
    auto_backup_prefix: str = "auto_vocab_"
    manual_backup_prefix: str = "manual_vocab_"
    pre_restore_backup_prefix: str = "pre_restore_vocab_"
    backup_lock_timeout_seconds: int = 600

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            raise ValueError("LOG_LEVEL noto‘g‘ri qiymat")
        return normalized

    @field_validator("admin_user_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str | set[int]) -> set[int]:
        if isinstance(value, set):
            return value
        if not value:
            return set()
        ids: set[int] = set()
        for part in str(value).split(","):
            part = part.strip()
            if not part:
                continue
            ids.add(int(part))
        return ids

    @field_validator("auto_backup_schedule")
    @classmethod
    def validate_backup_schedule(cls, value: str) -> str:
        normalized = value.lower()
        allowed = {"daily", "weekly", "monthly"}
        if normalized not in allowed:
            raise ValueError("AUTO_BACKUP_SCHEDULE noto‘g‘ri qiymat")
        return normalized

    @field_validator("auto_backup_hour")
    @classmethod
    def validate_backup_hour(cls, value: int) -> int:
        if not 0 <= value <= 23:
            raise ValueError("AUTO_BACKUP_HOUR noto‘g‘ri qiymat")
        return value

    @field_validator("auto_backup_minute")
    @classmethod
    def validate_backup_minute(cls, value: int) -> int:
        if not 0 <= value <= 59:
            raise ValueError("AUTO_BACKUP_MINUTE noto‘g‘ri qiymat")
        return value


settings = Settings()
