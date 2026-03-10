"""
DB接続・セッション管理。
同期セッションで FastAPI と組み合わせ。PostgreSQL / SQLite 両対応。
"""
import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base

logger = logging.getLogger(__name__)

_settings = get_settings()

# 同期用URL（PostgreSQL は psycopg2、SQLite はそのまま）
_sync_url = _settings.database_url.strip()

# DATABASE_URL が https:// のときは誤設定（WebのURLを入れた場合など）
if _sync_url.startswith("https://"):
    raise ValueError(
        "DATABASE_URL に https:// のURLが設定されています。"
        " PostgreSQL を使う場合は、Render の PostgreSQL サービス画面の "
        "「Internal Database URL」（postgresql:// で始まる文字列）を設定してください。"
    )
if _sync_url.startswith("postgres://") and "postgresql" not in _sync_url:
    _sync_url = "postgresql" + _sync_url[9:]  # postgres:// → postgresql://
if _sync_url.startswith("sqlite+aiosqlite"):
    _sync_url = _sync_url.replace("sqlite+aiosqlite", "sqlite")
if _sync_url.startswith("postgresql://") and "psycopg2" not in _sync_url:
    _sync_url = _sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)

sync_engine = create_engine(
    _sync_url,
    echo=_settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in _sync_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI Depends 用。同期セッションを yield。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """テーブル作成。起動時またはマイグレーション代わりに実行。"""
    Base.metadata.create_all(bind=sync_engine)
    # 既存DBに trip_type カラムが無い場合は追加（往復/片道対応）
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("ALTER TABLE expenses ADD COLUMN trip_type VARCHAR(16)"))
            conn.commit()
    except Exception:
        pass  # カラムが既に存在するなど
    # 既存DBに submitted_at カラムが無い場合は追加（提出日時）
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("ALTER TABLE expenses ADD COLUMN submitted_at DATETIME"))
            conn.commit()
    except Exception:
        pass
