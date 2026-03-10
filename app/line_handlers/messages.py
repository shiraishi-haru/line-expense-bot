"""
LINE 返信メッセージの文言を一元管理。
初心者向けの分かりやすい日本語で統一。
"""
from app.services.expense_parser import get_expense_format_example

# 登録フロー
MSG_REQUEST_INVITE_CODE = "招待コードを入力してください。"
MSG_INVITE_CODE_INVALID = "招待コードが正しくありません。管理者に確認してください。"
MSG_REQUEST_FULL_NAME = (
    "ありがとうございます。次に、フルネームを漢字で入力してください。\n例：白石温"
)
MSG_FULL_NAME_INVALID = "フルネームを漢字で入力してください。例：白石温"
MSG_REGISTRATION_DONE = "登録が完了しました。今後はこの名前で交通費を管理します：{full_name}"

# 登録直後の交通費入力案内
MSG_EXPENSE_FORMAT_AFTER_REGISTRATION = (
    "交通費は次の形式で送信してください。\n例：" + get_expense_format_example()
)

# 入力方法・使い方の全文（「入力方法」やリッチメニューで表示）
MSG_INPUT_GUIDE_FULL = """【交通費の入力】
次の形式でそのまま送信してください。
例：""" + get_expense_format_example() + """

【履歴確認】
「履歴」または「履歴確認」と送ると、登録した交通費の一覧を表示します。

【月別集計】
「月別集計」または「月別」と送ると、今月の交通費の合計を表示します。

【修正】
「完了」を送る前の未提出分だけ修正できます。
「修正 番号 日付 出発→到着 金額円 用途 往復または片道」で送信してください。番号は「履歴」で表示されるNo.の数字です。
例：修正 3 4/12 渋谷→新宿 220円 稽古 往復

【完了報告】
「完了」は月末に送信してください。送信すると未提出の交通費がまとめて提出され、管理者に通知されます。送信後は修正できません。"""

# 交通費入力
MSG_EXPENSE_FORMAT_ERROR = (
    "入力形式が違います。\n例：" + get_expense_format_example()
)
MSG_EXPENSE_REGISTERED = "交通費を登録しました：{date} {from_loc}→{to_loc} {amount}円 {trip}{purpose}"
MSG_EXPENSE_NOT_REGISTERED = "交通費を登録できませんでした。形式を確認してください。"

# 履歴・集計（{trip} は 往復/片道 の表示、空の場合は省略。{submitted} は提出日時）
MSG_NO_EXPENSES = "登録された交通費はありません。"
MSG_MONTHLY_SUMMARY_HEADER = "【{year}年{month}月】合計：{total}円\n"
MSG_EXPENSE_LINE = "{date} {from_loc}→{to_loc} {amount}円 {trip}{purpose}{submitted}\n"
MSG_EXPENSE_LINE_WITH_ID = "No.{id} {date} {from_loc}→{to_loc} {amount}円 {trip}{purpose}{submitted}\n"
MSG_COMPLETED_SENT = "完了報告を送信しました。{count}件の交通費を提出済みにしました。\n次回も月末に「完了」を送信してください。"
MSG_NO_DRAFT = "完了する交通費がありません。"
MSG_HISTORY_HEADER = "【履歴】修正するときは番号（No.）を覚えておいてください。\n"
MSG_EDIT_ONLY_DRAFT = "修正は「完了」する前のもののみ可能です。"
MSG_EDIT_SUCCESS = "No.{id} を修正しました：{date} {from_loc}→{to_loc} {amount}円 {trip}{purpose}"
MSG_EDIT_FAIL = "修正できませんでした。番号が正しいか、未提出（完了前）のものか確認してください。"
MSG_NOT_FOUND = "該当する交通費が見つかりません。"

# リッチメニュー用
MENU_INPUT_GUIDE = "交通費入力方法"
MENU_HISTORY = "履歴確認"
MENU_MONTHLY = "月別集計"
MENU_COMPLETE = "完了報告"

# 管理者通知
MSG_ADMIN_COMPLETED = "【交通費完了報告】\n{full_name} さんが完了報告を送信しました。（{count}件）"
