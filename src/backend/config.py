"""백엔드 환경변수 설정."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.shared.paths import APP_DB, CHROMA_DIR, PROJECT_ROOT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "청년정책도우미 API"
    db_path: Path = APP_DB
    chroma_dir: Path = CHROMA_DIR
    frontend_dist: Path = PROJECT_ROOT / "frontend" / "dist"


settings = Settings()
