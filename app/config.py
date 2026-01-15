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


settings = Settings()
