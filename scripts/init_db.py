#!/usr/bin/env python3
"""
DB初期化・招待コード投入。
例: python scripts/init_db.py
     INVITE_CODE=mycode python scripts/init_db.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import init_db, sync_engine
from app.db.models import InviteCode


def main():
    init_db()
    print("テーブルを作成しました。")

    code = os.environ.get("INVITE_CODE")
    if code:
        from sqlalchemy.orm import Session
        session = Session(bind=sync_engine)
        existing = session.query(InviteCode).filter(InviteCode.code == code).first()
        if not existing:
            session.add(InviteCode(code=code.strip(), is_active=True))
            session.commit()
            print(f"招待コードを追加しました: {code}")
        else:
            print(f"招待コードは既に存在します: {code}")
        session.close()


if __name__ == "__main__":
    main()
