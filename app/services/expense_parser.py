"""
交通費の自然文解析。
例：「4/12 渋谷→新宿 220円 稽古」から 日付・出発地・到着地・金額・用途 を抽出。
"""
import re
from datetime import datetime
from typing import Optional

from dateutil.parser import parse as date_parse


class ParsedExpense:
    """解析結果を保持するデータクラス"""

    __slots__ = ("date", "from_location", "to_location", "amount", "purpose", "trip_type")

    def __init__(
        self,
        date: datetime,
        from_location: str,
        to_location: str,
        amount: int,
        purpose: Optional[str] = None,
        trip_type: Optional[str] = None,
    ):
        self.date = date
        self.from_location = from_location
        self.to_location = to_location
        self.amount = amount
        self.purpose = purpose or ""
        self.trip_type = trip_type  # "round_trip" 往復 / "one_way" 片道

    def __repr__(self):
        return (
            f"ParsedExpense(date={self.date.date()}, "
            f"{self.from_location}→{self.to_location}, {self.amount}円, {self.purpose}, {self.trip_type})"
        )


# パターン例: 4/12 渋谷→新宿 220円 稽古
# 日付: 数字/数字 または 数字/数字/数字
# 区間: 〇〇→〇〇 （全角矢印も許容）
# 金額: 数字+円
# 用途: 残りすべて

DATE_PATTERNS = [
    r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)",  # 4/12 または 4/12/2025
    r"(\d{4}-\d{2}-\d{2})",  # 2025-04-12
]

ARROW = r"[→⇨➡]|から|→"  # 半角矢印・全角・から
LOCATION = r"[\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]+"  # 漢字・ひらがな・カタカナ・英数字
AMOUNT = r"(\d+)\s*円"

# 1. 日付を探す
# 2. 「出発→到着」を探す
# 3. 「数字円」を探す
# 4. 残りを用途とする


def parse_expense_text(text: str) -> Optional[ParsedExpense]:
    """
    自然文から交通費情報を抽出する。
    成功時は ParsedExpense、失敗時は None。
    """
    text = text.strip()
    if not text:
        return None

    # 日付
    date_obj = None
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            try:
                date_str = m.group(1)
                if "/" in date_str:
                    parts = date_str.split("/")
                    if len(parts) == 2:
                        y = datetime.now().year
                        date_obj = datetime(y, int(parts[0]), int(parts[1])).date()
                    else:
                        date_obj = datetime(
                            int(parts[2]) if len(parts[2]) == 4 else 2000 + int(parts[2]),
                            int(parts[0]),
                            int(parts[1]),
                        ).date()
                else:
                    date_obj = date_parse(date_str).date()
                break
            except (ValueError, IndexError):
                continue
    if date_obj is None:
        return None

    # 金額（数字+円）
    amount_match = re.search(AMOUNT, text)
    if not amount_match:
        return None
    amount = int(amount_match.group(1))

    # 区間（〇〇→〇〇）
    arrow_pattern = r"(.+?)\s*[→⇨➡]\s*(.+?)(?=\s+\d+円|\s*$)"
    route_match = re.search(arrow_pattern, text)
    if not route_match:
        # 「渋谷 新宿 220円」のように矢印なしの場合は、日付と金額の間を分割する別パターン
        parts = re.split(r"\s+", text, maxsplit=4)
        if len(parts) >= 4:
            # 日付, 出発, 到着, 金額円, 用途...
            from_loc = parts[1]
            to_loc = parts[2]
        else:
            return None
    else:
        from_loc = route_match.group(1).strip()
        to_loc = route_match.group(2).strip()
        # 先頭の日付部分を除く
        for pat in DATE_PATTERNS:
            from_loc = re.sub(r"^\s*" + pat + r"\s*", "", from_loc)
            break
        if not from_loc or not to_loc:
            return None

    # 用途：金額の後ろの文字列。末尾の「往復」「片道」を trip_type に分離
    purpose = ""
    trip_type = None
    if amount_match:
        after_amount = text[amount_match.end() :].strip()
        if after_amount:
            # 末尾が 往復 または 片道 なら trip_type にし、用途から除く
            for label, value in [("往復", "round_trip"), ("片道", "one_way")]:
                if after_amount.endswith(label):
                    trip_type = value
                    after_amount = after_amount[: -len(label)].strip()
                    break
                if after_amount.startswith(label + " ") or after_amount.startswith(label + "　"):
                    trip_type = value
                    after_amount = after_amount[len(label):].strip()
                    break
            purpose = after_amount

    return ParsedExpense(
        date=datetime.combine(date_obj, datetime.min.time()),
        from_location=from_loc,
        to_location=to_loc,
        amount=amount,
        purpose=purpose.strip(),
        trip_type=trip_type,
    )


def get_expense_format_example() -> str:
    """入力形式の例文を返す（Botメッセージ用）。"""
    return "4/12 渋谷→新宿 220円 稽古 往復"


def get_trip_type_display(trip_type: Optional[str]) -> str:
    """trip_type を表示用の日本語に。"""
    if trip_type == "round_trip":
        return "往復"
    if trip_type == "one_way":
        return "片道"
    return ""
