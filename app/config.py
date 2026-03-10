"""
アプリケーション設定。
環境変数から読み込み。.env ファイル対応。
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LINE
    line_channel_secret: str = ""
    line_channel_access_token: str = ""
    line_admin_user_id: Optional[str] = None  # 完了通知を送る管理者のLINE user ID

    # Database (PostgreSQL)
    database_url: str = "sqlite+aiosqlite:///./line_expense.db"
    # Render等では: postgresql+psycopg2://user:pass@host:5432/dbname

    # Google Sheets（任意・後から設定可）
    google_credentials_json_path: Optional[str] = None
    google_spreadsheet_id: Optional[str] = None

    # 招待コード（初回登録用・本番ではDBのInviteCodesから検証）
    # 開発用に1つ固定コードを設定することも可
    default_invite_code: Optional[str] = None

    # App
    app_env: str = "development"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
