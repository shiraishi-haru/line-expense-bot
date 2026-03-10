"""
交通費の登録・一覧・修正・完了処理。
"""
from datetime import date, datetime
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Expense, EXPENSE_STATUS_DRAFT, EXPENSE_STATUS_SUBMITTED, User
from app.services.expense_parser import ParsedExpense


def create_expense(
    db: Session,
    user_id: int,
    parsed: ParsedExpense,
) -> Expense:
    """1件の交通費をdraftで登録。片道＝入力金額のまま、往復＝入力金額の2倍を保存。"""
    expense_date = parsed.date.date() if hasattr(parsed.date, "date") else parsed.date
    # 往復の場合は金額を2倍にして保存（精算用の往復金額）
    amount = parsed.amount * 2 if parsed.trip_type == "round_trip" else parsed.amount
    e = Expense(
        user_id=user_id,
        date=expense_date,
        from_location=parsed.from_location,
        to_location=parsed.to_location,
        amount=amount,
        purpose=parsed.purpose or None,
        trip_type=parsed.trip_type,
        status=EXPENSE_STATUS_DRAFT,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def get_expenses_by_user(
    db: Session,
    user_id: int,
    *,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Expense]:
    """利用者の交通費一覧（新しい順）。"""
    q = db.query(Expense).filter(Expense.user_id == user_id)
    if status:
        q = q.filter(Expense.status == status)
    return q.order_by(Expense.date.desc(), Expense.id.desc()).limit(limit).all()


def get_expense_by_id(db: Session, expense_id: int, user_id: int) -> Optional[Expense]:
    """1件取得（本人のみ）。"""
    return (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.user_id == user_id)
        .first()
    )


def update_expense(
    db: Session,
    expense_id: int,
    user_id: int,
    parsed: ParsedExpense,
) -> Optional[Expense]:
    """draft の交通費を更新。"""
    e = get_expense_by_id(db, expense_id, user_id)
    if not e or e.status != EXPENSE_STATUS_DRAFT:
        return None
    expense_date = parsed.date.date() if hasattr(parsed.date, "date") else parsed.date
    e.date = expense_date
    e.from_location = parsed.from_location
    e.to_location = parsed.to_location
    # 往復の場合は金額を2倍にして保存
    e.amount = parsed.amount * 2 if parsed.trip_type == "round_trip" else parsed.amount
    e.purpose = parsed.purpose or None
    e.trip_type = parsed.trip_type
    db.commit()
    db.refresh(e)
    return e


def submit_expense(db: Session, expense_id: int, user_id: int) -> Optional[Expense]:
    """1件を submitted にする。"""
    e = get_expense_by_id(db, expense_id, user_id)
    if not e or e.status != EXPENSE_STATUS_DRAFT:
        return None
    e.status = EXPENSE_STATUS_SUBMITTED
    e.submitted_at = datetime.now()
    db.commit()
    db.refresh(e)
    return e


def get_monthly_summary_by_user(
    db: Session,
    user_id: int,
    year: int,
    month: int,
) -> Tuple[List[Expense], int]:
    """指定月の交通費一覧と合計金額。"""
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1)
    from sqlalchemy import and_

    items = (
        db.query(Expense)
        .filter(
            Expense.user_id == user_id,
            Expense.date >= start,
            Expense.date < end,
        )
        .order_by(Expense.date, Expense.id)
        .all()
    )
    total = sum(e.amount for e in items)
    return items, total


def get_all_users_monthly_summary(
    db: Session,
    year: int,
    month: int,
) -> List[Tuple[User, List[Expense], int]]:
    """管理者用：指定月の全利用者ごとの一覧と合計。"""
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1)
    users = db.query(User).filter(User.registration_status == "active").all()
    result = []
    for user in users:
        items = (
            db.query(Expense)
            .filter(
                Expense.user_id == user.id,
                Expense.date >= start,
                Expense.date < end,
            )
            .order_by(Expense.date, Expense.id)
            .all()
        )
        total = sum(e.amount for e in items)
        result.append((user, items, total))
    return result


def get_draft_expenses(db: Session, user_id: int) -> List[Expense]:
    """完了前（draft）の一覧。"""
    return get_expenses_by_user(db, user_id, status=EXPENSE_STATUS_DRAFT)


def submit_all_drafts_for_user(db: Session, user_id: int) -> int:
    """利用者が「完了」送信したときに、そのユーザーの全draftをsubmittedにする。戻り値は処理件数。"""
    now = datetime.now()
    drafts = get_draft_expenses(db, user_id)
    for e in drafts:
        e.status = EXPENSE_STATUS_SUBMITTED
        e.submitted_at = now
    db.commit()
    return len(drafts)
