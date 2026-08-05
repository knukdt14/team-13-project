"""백엔드 환경변수 설정."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.shared.paths import APP_DB, PROJECT_ROOT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "청년정책도우미 API"
    db_path: Path = APP_DB
    frontend_dist: Path = PROJECT_ROOT / "frontend" / "dist"

    # 컨테이너 분리 후 AI 서비스 주소. compose 에서는 서비스 이름(ai)으로 붙고,
    # 로컬에서 세 프로세스를 직접 띄울 때는 localhost 로 붙는다.
    ai_service_url: str = "http://localhost:9000"


settings = Settings()
