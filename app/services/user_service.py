"""
ユーザー登録・取得・招待コード検証。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import (
    REGISTRATION_STATUS_ACTIVE,
    REGISTRATION_STATUS_WAITING_INVITE,
    REGISTRATION_STATUS_WAITING_NAME,
    InviteCode,
    User,
)


def get_user_by_line_id(db: Session, line_user_id: str) -> Optional[User]:
    return db.query(User).filter(User.line_user_id == line_user_id).first()


def validate_invite_code(db: Session, code: str) -> bool:
    """招待コードが有効かどうか。DBに存在し is_active なら True。"""
    if not code or not code.strip():
        return False
    code = code.strip()
    row = db.query(InviteCode).filter(InviteCode.code == code, InviteCode.is_active == True).first()
    if row:
        return True
    # 設定にデフォルト招待コードがあればそれも許可
    settings = get_settings()
    if settings.default_invite_code and code == settings.default_invite_code:
        return True
    return False


def create_or_update_user(
    db: Session,
    line_user_id: str,
    line_display_name: Optional[str] = None,
    *,
    invite_code: Optional[str] = None,
    full_name_kanji: Optional[str] = None,
    registration_status: Optional[str] = None,
) -> User:
    """
    ユーザーが存在しなければ作成、存在すれば更新。
    登録フロー中は invite_code / full_name_kanji / registration_status を渡して更新。
    """
    user = get_user_by_line_id(db, line_user_id)
    if user is None:
        user = User(
            line_user_id=line_user_id,
            line_display_name=line_display_name,
            registration_status=REGISTRATION_STATUS_WAITING_INVITE,
        )
        db.add(user)
        db.flush()
    else:
        if line_display_name is not None:
            user.line_display_name = line_display_name

    if invite_code is not None:
        user.invite_code_used = invite_code
    if full_name_kanji is not None:
        user.full_name_kanji = full_name_kanji
    if registration_status is not None:
        user.registration_status = registration_status

    db.commit()
    db.refresh(user)
    return user


def complete_registration(db: Session, line_user_id: str, full_name_kanji: str) -> Optional[User]:
    """名前を保存し登録完了にする。"""
    user = get_user_by_line_id(db, line_user_id)
    if not user:
        return None
    user.full_name_kanji = full_name_kanji
    user.registration_status = REGISTRATION_STATUS_ACTIVE
    db.commit()
    db.refresh(user)
    return user


def set_status_waiting_name(db: Session, line_user_id: str) -> Optional[User]:
    user = get_user_by_line_id(db, line_user_id)
    if not user:
        return None
    user.registration_status = REGISTRATION_STATUS_WAITING_NAME
    db.commit()
    db.refresh(user)
    return user
