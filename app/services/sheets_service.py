"""
Googleスプレッドシートへの書き込み。
・全履歴シート
・月別集計シート
・利用者別シート
出力時の利用者名は full_name_kanji を使用。
"""
import json
import logging
import os
from datetime import date
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Expense, User
from app.services.expense_parser import get_trip_type_display

logger = logging.getLogger(__name__)


def _get_client():
    """gspread の認証クライアント。環境変数 JSON またはサービスアカウントファイルを参照。"""
    import gspread
    from google.oauth2.service_account import Credentials

    settings = get_settings()
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # 1) 環境変数 GOOGLE_CREDENTIALS_JSON に JSON 文字列が入っている場合（Render 等でファイルを置けないとき）
    raw_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if raw_json:
        try:
            info = json.loads(raw_json)
            creds = Credentials.from_service_account_info(info, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            logger.warning("スプレッドシート: GOOGLE_CREDENTIALS_JSON の解析に失敗しました: %s", e)
            return None

    # 2) ファイルパスで指定されている場合（ローカルや Secret File 利用時）
    path = settings.google_credentials_json_path or os.environ.get("GOOGLE_CREDENTIALS_JSON_PATH")
    if not path:
        logger.info(
            "スプレッドシート: 認証が未設定です。"
            " GOOGLE_CREDENTIALS_JSON（JSON文字列）または GOOGLE_CREDENTIALS_JSON_PATH（ファイルパス）を設定してください。"
        )
        return None
    if not os.path.isfile(path):
        logger.warning("スプレッドシート: 認証ファイルが見つかりません: %s", path)
        return None
    creds = Credentials.from_service_account_file(path, scopes=scopes)
    return gspread.authorize(creds)


def _get_spreadsheet():
    """スプレッドシートを取得。"""
    client = _get_client()
    if not client:
        return None
    settings = get_settings()
    sheet_id = settings.google_spreadsheet_id or os.environ.get("GOOGLE_SPREADSHEET_ID")
    if not sheet_id:
        logger.info("スプレッドシート: GOOGLE_SPREADSHEET_ID が未設定です。")
        return None
    return client.open_by_key(sheet_id)


def _ensure_sheet(spreadsheet, title: str, headers: List[str]):
    """シートがなければ作成し、ヘッダー行を書く。"""
    try:
        sheet = spreadsheet.worksheet(title)
    except Exception:
        sheet = spreadsheet.add_worksheet(title=title, rows=500, cols=10)
    # 1行目をヘッダーに
    sheet.clear()
    sheet.append_row(headers)
    return sheet


def _row_expense(expense: Expense, full_name: str) -> List[str]:
    """1件の経費をシート用の行リストに。"""
    d = expense.date
    if hasattr(d, "date"):
        d = d.date() if callable(getattr(d, "date", None)) else d
    trip_display = get_trip_type_display(getattr(expense, "trip_type", None))
    submitted = getattr(expense, "submitted_at", None)
    submitted_str = submitted.strftime("%Y-%m-%d %H:%M") if submitted and hasattr(submitted, "strftime") else ""
    return [
        str(d),
        full_name,
        expense.from_location,
        expense.to_location,
        str(expense.amount),
        trip_display,
        expense.purpose or "",
        expense.status,
        submitted_str,
    ]


def sync_all_expenses(db: Session) -> bool:
    """
    全履歴シートを更新。
    提出者（氏名）ごとにまとめて並べる。列: 日付, 氏名, 出発地, 到着地, 金額, 用途, ステータス
    """
    spreadsheet = _get_spreadsheet()
    if not spreadsheet:
        return False
    headers = ["日付", "氏名", "出発地", "到着地", "金額", "往復/片道", "用途", "ステータス", "提出日時"]
    sheet = _ensure_sheet(spreadsheet, "全履歴", headers)
    # 提出者（氏名）順→日付順で並べ、集計しやすくする
    expenses = (
        db.query(Expense)
        .join(User)
        .order_by(func.coalesce(User.full_name_kanji, "zzz"), Expense.date, Expense.id)
        .all()
    )
    rows = []
    for e in expenses:
        user = e.user
        name = (user.full_name_kanji or user.line_display_name or "未登録")
        rows.append(_row_expense(e, name))
    if rows:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
    return True


def sync_submitter_summary(db: Session) -> bool:
    """
    提出者別集計シートを更新（管理者用・全体の合計）。
    列: 氏名, 件数, 合計金額
    """
    spreadsheet = _get_spreadsheet()
    if not spreadsheet:
        return False
    headers = ["氏名", "件数", "合計金額"]
    sheet = _ensure_sheet(spreadsheet, "提出者別集計", headers)
    q = (
        db.query(
            User.full_name_kanji,
            func.count(Expense.id).label("cnt"),
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
        )
        .outerjoin(Expense, User.id == Expense.user_id)
        .filter(User.registration_status == "active")
        .group_by(User.id)
        .order_by(func.coalesce(User.full_name_kanji, "zzz"))
    )
    rows = []
    for row in q:
        name = row.full_name_kanji or "未登録"
        rows.append([name, row.cnt, row.total])
    if rows:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
    return True


def sync_monthly_sheet(db: Session, year: int, month: int) -> bool:
    """
    月別集計シートを更新。提出者（氏名）ごとにまとめて並べる。
    シート名例: 2025年4月
    列: 日付, 氏名, 出発地, 到着地, 金額, 用途, ステータス
    """
    spreadsheet = _get_spreadsheet()
    if not spreadsheet:
        return False
    title = f"{year}年{month}月"
    headers = ["日付", "氏名", "出発地", "到着地", "金額", "往復/片道", "用途", "ステータス", "提出日時"]
    sheet = _ensure_sheet(spreadsheet, title, headers)
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1)
    expenses = (
        db.query(Expense)
        .join(User)
        .filter(Expense.date >= start, Expense.date < end)
        .order_by(func.coalesce(User.full_name_kanji, "zzz"), Expense.date, Expense.id)
        .all()
    )
    rows = [_row_expense(e, e.user.full_name_kanji or e.user.line_display_name or "未登録") for e in expenses]
    if rows:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
    return True


def sync_monthly_submitter_summary(db: Session, year: int, month: int) -> bool:
    """
    月別・提出者別集計シートを更新（管理者用）。
    シート名例: 2025年3月_提出者別
    列: 氏名, 件数, 合計金額
    """
    spreadsheet = _get_spreadsheet()
    if not spreadsheet:
        return False
    title = f"{year}年{month}月_提出者別"
    headers = ["氏名", "件数", "合計金額"]
    sheet = _ensure_sheet(spreadsheet, title, headers)
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1)
    q = (
        db.query(
            User.full_name_kanji,
            func.count(Expense.id).label("cnt"),
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
        )
        .join(Expense, User.id == Expense.user_id)
        .filter(Expense.date >= start, Expense.date < end)
        .group_by(User.id)
        .order_by(func.coalesce(User.full_name_kanji, "zzz"))
    )
    rows = []
    for row in q:
        name = row.full_name_kanji or "未登録"
        rows.append([name, row.cnt, row.total])
    if rows:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
    return True


def sync_user_sheet(db: Session, user: User) -> bool:
    """
    利用者別シートを更新。
    シート名: 利用者名（full_name_kanji）※使えない文字は置換する想定
    """
    spreadsheet = _get_spreadsheet()
    if not spreadsheet:
        return False
    name = user.full_name_kanji or user.line_display_name or "未登録"
    # シート名に使えない文字を置換
    for c in ["/", "\\", "?", "*", "[", "]"]:
        name = name.replace(c, "_")
    title = name[:100]
    headers = ["日付", "出発地", "到着地", "金額", "往復/片道", "用途", "ステータス", "提出日時"]
    sheet = _ensure_sheet(spreadsheet, title, headers)
    expenses = (
        db.query(Expense)
        .filter(Expense.user_id == user.id)
        .order_by(Expense.date.desc(), Expense.id.desc())
        .all()
    )
    rows = []
    for e in expenses:
        d = e.date
        if hasattr(d, "date"):
            d = d.date() if callable(getattr(d, "date", None)) else d
        submitted = getattr(e, "submitted_at", None)
        submitted_str = submitted.strftime("%Y-%m-%d %H:%M") if submitted and hasattr(submitted, "strftime") else ""
        rows.append([
            str(d),
            e.from_location,
            e.to_location,
            str(e.amount),
            get_trip_type_display(getattr(e, "trip_type", None)),
            e.purpose or "",
            e.status,
            submitted_str,
        ])
    if rows:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
    return True
