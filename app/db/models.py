"""
SQLAlchemy モデル定義。
PostgreSQL 移行を想定し、型・制約を明示。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# 会話状態（登録フロー用）
REGISTRATION_STATUS_WAITING_INVITE = "waiting_invite_code"
REGISTRATION_STATUS_WAITING_NAME = "waiting_full_name"
REGISTRATION_STATUS_ACTIVE = "active"

# ユーザーロール
ROLE_USER = "user"
ROLE_ADMIN = "admin"

# 経費ステータス
EXPENSE_STATUS_DRAFT = "draft"
EXPENSE_STATUS_SUBMITTED = "submitted"


class User(Base):
    """利用者テーブル"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    line_user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    line_display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name_kanji: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    role: Mapped[str] = mapped_column(String(16), default=ROLE_USER, nullable=False)
    invite_code_used: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    registration_status: Mapped[str] = mapped_column(
        String(32), default=REGISTRATION_STATUS_WAITING_INVITE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    expenses: Mapped[list["Expense"]] = relationship("Expense", back_populates="user")


class Expense(Base):
    """交通費テーブル"""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    from_location: Mapped[str] = mapped_column(String(128), nullable=False)
    to_location: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # 円単位
    purpose: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trip_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # "round_trip" 往復 / "one_way" 片道
    status: Mapped[str] = mapped_column(String(16), default=EXPENSE_STATUS_DRAFT, nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # 完了報告した日時
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="expenses")


class InviteCode(Base):
    """招待コードテーブル"""

    __tablename__ = "invite_codes"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
