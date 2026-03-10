"""
LINE Webhook のメッセージ・ポストバック処理。
登録状態に応じて分岐し、交通費登録・履歴・月別集計・完了報告を行う。
"""
import logging
from datetime import datetime
from typing import Optional

from linebot.models import MessageEvent, TextMessage, PostbackEvent
from sqlalchemy.orm import Session

from app.db.models import REGISTRATION_STATUS_ACTIVE, REGISTRATION_STATUS_WAITING_INVITE, REGISTRATION_STATUS_WAITING_NAME
from app.line_handlers.messages import (
    MSG_ADMIN_COMPLETED,
    MSG_COMPLETED_SENT,
    MSG_EDIT_ONLY_DRAFT,
    MSG_EDIT_FAIL,
    MSG_EDIT_SUCCESS,
    MSG_EXPENSE_FORMAT_AFTER_REGISTRATION,
    MSG_EXPENSE_FORMAT_ERROR,
    MSG_EXPENSE_LINE,
    MSG_EXPENSE_LINE_WITH_ID,
    MSG_EXPENSE_NOT_REGISTERED,
    MSG_EXPENSE_REGISTERED,
    MSG_FULL_NAME_INVALID,
    MSG_HISTORY_HEADER,
    MSG_INPUT_GUIDE_FULL,
    MSG_INVITE_CODE_INVALID,
    MSG_MONTHLY_SUMMARY_HEADER,
    MSG_NO_DRAFT,
    MSG_NO_EXPENSES,
    MSG_NOT_FOUND,
    MSG_REGISTRATION_DONE,
    MSG_REQUEST_FULL_NAME,
    MSG_REQUEST_INVITE_CODE,
)
from app.services.expense_parser import get_expense_format_example, get_trip_type_display, parse_expense_text
from app.services.expense_service import (
    create_expense,
    get_draft_expenses,
    get_expenses_by_user,
    get_monthly_summary_by_user,
    submit_all_drafts_for_user,
    update_expense,
)
from app.services.user_service import (
    complete_registration,
    create_or_update_user,
    get_user_by_line_id,
    set_status_waiting_name,
    validate_invite_code,
)
from app.services.sheets_service import (
    sync_all_expenses,
    sync_monthly_sheet,
    sync_monthly_submitter_summary,
    sync_submitter_summary,
    sync_user_sheet,
)

logger = logging.getLogger(__name__)


def _is_kanji_name(text: str) -> bool:
    """漢字でフルネームが入力されているか簡易判定。"""
    text = text.strip()
    if len(text) < 2 or len(text) > 32:
        return False
    # 漢字・ひらがな・カタカナのみ許可（スペースは不可）
    for c in text:
        if c.isspace():
            return False
        if not (
            "\u4e00" <= c <= "\u9fff"
            or "\u3040" <= c <= "\u309f"
            or "\u30a0" <= c <= "\u30ff"
        ):
            return False
    return True


def _reply_text(line_bot_api, event, text: str) -> None:
    """テキストで返信。"""
    line_bot_api.reply_message(event.reply_token, TextMessage(text=text))


def _normalize_keyword(text: str) -> str:
    """キーワード判定用：前後空白を削除し、内部の空白もすべて除く。"""
    return "".join(text.strip().split())


def handle_webhook_events(line_bot_api, events: list, db: Session) -> None:
    """受信したイベントを順に処理。"""
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
            _handle_text(line_bot_api, event, event.message.text.strip(), db)
        elif isinstance(event, PostbackEvent):
            _handle_postback(line_bot_api, event, db)


def _handle_text(line_bot_api, event, text: str, db: Session) -> None:
    line_user_id = event.source.user_id
    profile = None
    try:
        profile = line_bot_api.get_profile(line_user_id)
    except Exception:
        pass
    line_display_name = profile.display_name if profile else None

    # ユーザー取得または作成（未登録なら waiting_invite_code）
    user = get_user_by_line_id(db, line_user_id)
    if user is None:
        user = create_or_update_user(
            db, line_user_id, line_display_name, registration_status=REGISTRATION_STATUS_WAITING_INVITE
        )

    status = user.registration_status

    # 登録中は交通費処理に進めず、登録フローを優先
    if status == REGISTRATION_STATUS_WAITING_INVITE:
        if validate_invite_code(db, text):
            set_status_waiting_name(db, line_user_id)
            create_or_update_user(db, line_user_id, line_display_name, invite_code=text)
            _reply_text(line_bot_api, event, MSG_REQUEST_FULL_NAME)
        else:
            _reply_text(line_bot_api, event, MSG_INVITE_CODE_INVALID)
        return

    if status == REGISTRATION_STATUS_WAITING_NAME:
        if _is_kanji_name(text):
            complete_registration(db, line_user_id, text.strip())
            # 登録完了メッセージと交通費入力例を2通で返す
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextMessage(text=MSG_REGISTRATION_DONE.format(full_name=text.strip())),
                    TextMessage(text=MSG_EXPENSE_FORMAT_AFTER_REGISTRATION),
                ],
            )
        else:
            _reply_text(line_bot_api, event, MSG_FULL_NAME_INVALID)
        return

    # active のときのみ以下を処理
    if status != REGISTRATION_STATUS_ACTIVE:
        _reply_text(line_bot_api, event, MSG_REQUEST_INVITE_CODE)
        return

    # 表示名の更新だけしておく
    if line_display_name and user.line_display_name != line_display_name:
        create_or_update_user(db, line_user_id, line_display_name)

    user = get_user_by_line_id(db, line_user_id)
    if not user:
        return

    # キーワードで分岐（空白・全角スペース含めても認識）
    n = _normalize_keyword(text)
    if n == "完了":
        _handle_complete(line_bot_api, event, user, db)
        return
    if n in ("履歴", "履歴確認", "れきし"):
        _handle_history(line_bot_api, event, user, db)
        return
    if n in ("月別集計", "月別", "つきべつ"):
        _handle_monthly(line_bot_api, event, user, db)
        return
    if n in ("交通費入力方法", "入力方法", "れい"):
        _reply_text(line_bot_api, event, MSG_INPUT_GUIDE_FULL)
        return
    # 修正：「修正 番号 日付 出発→到着 金額円 用途」
    if text.strip().startswith("修正 ") and len(text.strip()) > 3:
        rest = text.strip()[3:].strip()
        parts = rest.split(None, 1)
        if len(parts) == 2 and parts[0].isdigit():
            try:
                expense_id = int(parts[0])
                parsed = parse_expense_text(parts[1])
                if parsed:
                    updated = update_expense(db, expense_id, user.id, parsed)
                    if updated:
                        date_str = parsed.date.strftime("%m/%d") if hasattr(parsed.date, "strftime") else str(parsed.date)
                        trip_d = get_trip_type_display(parsed.trip_type)
                        trip_s = (trip_d + " ") if trip_d else ""
                        _reply_text(
                            line_bot_api,
                            event,
                            MSG_EDIT_SUCCESS.format(
                                id=expense_id,
                                date=date_str,
                                from_loc=parsed.from_location,
                                to_loc=parsed.to_location,
                                amount=parsed.amount,
                                trip=trip_s,
                                purpose=parsed.purpose or "",
                            ),
                        )
                        try:
                            sync_all_expenses(db)
                        except Exception:
                            pass
                    else:
                        _reply_text(line_bot_api, event, MSG_EDIT_FAIL)
                else:
                    _reply_text(line_bot_api, event, MSG_EDIT_FAIL)
            except ValueError:
                _reply_text(line_bot_api, event, MSG_EDIT_FAIL)
        else:
            _reply_text(line_bot_api, event, MSG_EDIT_FAIL)
        return
    # 管理者設定用：送信者のLINE user ID を返す
    if n in ("マイID", "userid", "ユーザーID"):
        _reply_text(
            line_bot_api,
            event,
            f"あなたのLINE user ID は次のとおりです。管理者通知を受け取る場合は、.env の LINE_ADMIN_USER_ID にこの値を設定してください。\n\n{line_user_id}",
        )
        return

    # それ以外は交通費として解析を試みる
    parsed = parse_expense_text(text)
    if parsed:
        create_expense(db, user.id, parsed)
        # 交通費登録のたびにスプシへ同期（設定されていれば）
        try:
            sync_all_expenses(db)
        except Exception:
            pass
        date_str = parsed.date.strftime("%m/%d") if hasattr(parsed.date, "strftime") else str(parsed.date)
        trip_d = get_trip_type_display(parsed.trip_type)
        trip_s = (trip_d + " ") if trip_d else ""
        _reply_text(
            line_bot_api,
            event,
            MSG_EXPENSE_REGISTERED.format(
                date=date_str,
                from_loc=parsed.from_location,
                to_loc=parsed.to_location,
                amount=parsed.amount,
                trip=trip_s,
                purpose=parsed.purpose or "",
            ),
        )
    else:
        _reply_text(line_bot_api, event, MSG_EXPENSE_FORMAT_ERROR)


def _handle_postback(line_bot_api, event: PostbackEvent, db: Session) -> None:
    data = event.postback.data
    line_user_id = event.source.user_id
    user = get_user_by_line_id(db, line_user_id)
    if not user or user.registration_status != REGISTRATION_STATUS_ACTIVE:
        _reply_text(line_bot_api, event, MSG_REQUEST_INVITE_CODE)
        return
    if data == "action=history":
        _handle_history(line_bot_api, event, user, db)
    elif data == "action=monthly":
        _handle_monthly(line_bot_api, event, user, db)
    elif data == "action=complete":
        _handle_complete(line_bot_api, event, user, db)
    elif data == "action=input_guide":
        _reply_text(line_bot_api, event, MSG_INPUT_GUIDE_FULL)


def _handle_history(line_bot_api, event, user, db: Session) -> None:
    expenses = get_expenses_by_user(db, user.id, limit=20)
    if not expenses:
        _reply_text(line_bot_api, event, MSG_NO_EXPENSES)
        return
    lines = [MSG_HISTORY_HEADER]
    for e in expenses:
        d = e.date.strftime("%m/%d") if hasattr(e.date, "strftime") else str(e.date)
        trip_d = get_trip_type_display(getattr(e, "trip_type", None))
        trip_s = (trip_d + " ") if trip_d else ""
        submitted = getattr(e, "submitted_at", None)
        submitted_s = (" 提出: " + submitted.strftime("%Y-%m-%d %H:%M")) if submitted and hasattr(submitted, "strftime") else ""
        lines.append(
            MSG_EXPENSE_LINE_WITH_ID.format(
                id=e.id,
                date=d,
                from_loc=e.from_location,
                to_loc=e.to_location,
                amount=e.amount,
                trip=trip_s,
                purpose=e.purpose or "",
                submitted=submitted_s,
            ).strip() + "\n"
        )
    _reply_text(line_bot_api, event, "".join(lines))


def _handle_monthly(line_bot_api, event, user, db: Session) -> None:
    now = datetime.now()
    items, total = get_monthly_summary_by_user(db, user.id, now.year, now.month)
    if not items:
        _reply_text(line_bot_api, event, MSG_NO_EXPENSES)
        return
    msg = MSG_MONTHLY_SUMMARY_HEADER.format(year=now.year, month=now.month, total=total)
    for e in items:
        d = e.date.strftime("%m/%d") if hasattr(e.date, "strftime") else str(e.date)
        trip_d = get_trip_type_display(getattr(e, "trip_type", None))
        trip_s = (trip_d + " ") if trip_d else ""
        submitted = getattr(e, "submitted_at", None)
        submitted_s = (" 提出: " + submitted.strftime("%Y-%m-%d %H:%M")) if submitted and hasattr(submitted, "strftime") else ""
        msg += MSG_EXPENSE_LINE.format(
            date=d,
            from_loc=e.from_location,
            to_loc=e.to_location,
            amount=e.amount,
            trip=trip_s,
            purpose=e.purpose or "",
            submitted=submitted_s,
        ).strip() + "\n"
    _reply_text(line_bot_api, event, msg.strip())


def _handle_complete(line_bot_api, event, user, db: Session) -> None:
    count = submit_all_drafts_for_user(db, user.id)
    if count == 0:
        _reply_text(line_bot_api, event, MSG_NO_DRAFT)
        return
    _reply_text(line_bot_api, event, MSG_COMPLETED_SENT.format(count=count))
    # スプレッドシート同期（GOOGLE_CREDENTIALS_JSON_PATH と GOOGLE_SPREADSHEET_ID が設定されている場合）
    try:
        sync_all_expenses(db)
        now = datetime.now()
        sync_monthly_sheet(db, now.year, now.month)
        sync_monthly_submitter_summary(db, now.year, now.month)
        sync_submitter_summary(db)
        sync_user_sheet(db, user)
    except Exception:
        pass
    # 管理者へ通知（LINEの user ID は "U" で始まる33文字の文字列。.env には「マイID」で取得した値をそのまま設定）
    from app.config import get_settings
    settings = get_settings()
    admin_id = (settings.line_admin_user_id or "").strip()
    if not admin_id:
        logger.info("完了報告: LINE_ADMIN_USER_ID が未設定のため管理者へ通知しません")
    elif not admin_id.startswith("U") or len(admin_id) < 20:
        logger.warning(
            "完了報告: LINE_ADMIN_USER_ID の形式が正しくありません。"
            "管理者がBotに「マイID」と送り、表示された U で始まる長いIDを .env に設定してください。現在の値: %s",
            admin_id[:20] + "..." if len(admin_id) > 20 else admin_id,
        )
    elif not user.full_name_kanji:
        logger.warning("完了報告: 利用者の full_name_kanji が未設定のため管理者へ通知しません")
    else:
        try:
            line_bot_api.push_message(
                admin_id,
                TextMessage(
                    text=MSG_ADMIN_COMPLETED.format(
                        full_name=user.full_name_kanji,
                        count=count,
                    )
                ),
            )
            logger.info("完了報告: 管理者へ通知を送信しました")
        except Exception as e:
            logger.warning("完了報告: 管理者への通知に失敗しました error=%s", e)
