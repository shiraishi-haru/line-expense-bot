# LINE交通費精算Bot

身内向けに交通費精算をLINEで行うBotです。  
LINE Messaging API + FastAPI + SQLAlchemy（PostgreSQL/SQLite）+ Googleスプレッドシート連携。

---

## プロジェクト構成

```
課題5-3-2 LINE交通費/
├── app/
│   ├── __init__.py
│   ├── config.py              # 設定（環境変数）
│   ├── main.py                # FastAPI アプリ・Webhook エンドポイント
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py          # SQLAlchemy モデル（Users, Expenses, InviteCodes）
│   │   └── session.py        # DB接続・get_db・init_db
│   ├── line_handlers/
│   │   ├── __init__.py
│   │   ├── messages.py       # 返信メッセージ文言
│   │   └── webhook_handler.py # メッセージ・ポストバック処理
│   └── services/
│       ├── __init__.py
│       ├── expense_parser.py  # 自然文解析（交通費）
│       ├── expense_service.py # 交通費CRUD・月別集計・完了
│       ├── user_service.py   # ユーザー登録・招待コード検証
│       └── sheets_service.py # Googleスプレッドシート連携
├── scripts/
│   └── init_db.py            # テーブル作成・招待コード投入
├── .env.example
├── requirements.txt
├── run.py                     # ローカル起動
├── render.yaml                # Render デプロイ用
├── DEPLOY.md                  # デプロイ手順
└── SETUP.md                   # 初心者向けセットアップ手順
```

---

## 環境変数一覧

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `LINE_CHANNEL_SECRET` | ○ | LINE チャネルシークレット |
| `LINE_CHANNEL_ACCESS_TOKEN` | ○ | LINE チャネルアクセストークン |
| `LINE_ADMIN_USER_ID` | - | 完了報告を送る管理者のLINE user ID |
| `DATABASE_URL` | ○ | DB接続URL（例: `sqlite:///./line_expense.db` または `postgresql://...`） |
| `DEFAULT_INVITE_CODE` | - | 開発用のデフォルト招待コード（DBにコードが無い場合に使用） |
| `GOOGLE_CREDENTIALS_JSON_PATH` | - | サービスアカウントJSONのパス |
| `GOOGLE_SPREADSHEET_ID` | - | 出力先スプレッドシートID |
| `APP_ENV` | - | `development` / `production` |
| `DEBUG` | - | ログ詳細化 |

---

## クイックスタート（ローカル）

1. リポジトリをクローンし、`cd` でプロジェクトルートへ。
2. `python -m venv venv` で仮想環境を作成。
3. `source venv/bin/activate`（Windowsは `venv\Scripts\activate`）。
4. `pip install -r requirements.txt`
5. `.env.example` をコピーして `.env` を作成し、LINEの値と必要に応じて `DEFAULT_INVITE_CODE` を設定。
6. `python scripts/init_db.py` でテーブル作成。招待コードを追加する場合:  
   `INVITE_CODE=mycode python scripts/init_db.py`
7. `python run.py` で起動（http://localhost:8000）。
8. ngrok 等で https を公開し、LINE Developers の Webhook URL に `https://xxx/webhook` を設定。

詳細は **SETUP.md** を参照してください。

---

## 交通費入力形式（自然文）

例：

- `4/12 渋谷→新宿 220円 稽古`
- `5/3 新宿→池袋 180円 打ち合わせ`

抽出項目：日付・出発地・到着地・金額・用途。

---

## 利用者フロー

1. QRコードから友だち追加
2. 初回は「招待コード」入力 → 「フルネーム（漢字）」入力で登録完了
3. 交通費を自然文で送信して登録
4. 「履歴確認」「月別集計」で表示
5. 「完了」送信で提出済みにし、管理者へ通知（`LINE_ADMIN_USER_ID` 設定時）

---

## Googleスプレッドシートへの集計出力

**場所**: `app/services/sheets_service.py`

利用者が「**完了**」を送信すると、次の3種類のシートが更新されます（環境変数が設定されている場合のみ）。

| シート | 内容 |
|--------|------|
| **全履歴** | 全員の交通費を日付の新しい順で出力 |
| **〇〇年〇月**（月別） | その月の全員分の交通費 |
| **利用者名**（利用者別） | その利用者の全件 |

**有効にするには** `.env` に次を設定してください。

- `GOOGLE_CREDENTIALS_JSON_PATH` … サービスアカウントのJSONキーファイルのパス
- `GOOGLE_SPREADSHEET_ID` … 出力先スプレッドシートのID（URLの `/d/` と `/edit` の間）

スプレッドシート側で、サービスアカウントのメールアドレスを編集者として共有してください。設定手順の詳細は **DEPLOY.md** の「Googleスプレッドシート連携」を参照してください。

---

## ライセンス

利用規約に従ってください。
