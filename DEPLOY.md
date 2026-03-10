# Render デプロイ手順（LINE交通費精算Bot）

Render で Web サービスと PostgreSQL を用意し、LINE Webhook を本番運用する手順です。**Git にコードをアップするところから**順に説明します。

---

## 1. Git にコードをアップする

Render は GitHub（または GitLab）のリポジトリと連携してデプロイするため、まずプロジェクトを Git で管理し、リモートにプッシュします。

### 1-1. 必要なもの

- [Git](https://git-scm.com/) がインストールされていること
- [GitHub](https://github.com/) のアカウントがあること

### 1-2. リポジトリを初期化する（まだの場合）

プロジェクトフォルダで、まだ Git を使っていない場合は次を実行します。

```bash
cd "/Users/shiraishiatsushi/コンテンツ用/課題5-3-2 LINE交通費"
git init
```

※ すでに `git init` 済みの場合はこの手順は不要です。

### 1-3. .gitignore を確認する

`.env` や仮想環境、DBファイルをリポジトリに含めないため、プロジェクトルートに **.gitignore** があります。次のような内容になっていることを確認してください（なければそのまま作成されています）。

- `.env` … 秘密情報が書かれたファイル（**絶対にコミットしない**）
- `venv/` … 仮想環境
- `*.db` … ローカル用SQLite
- `__pycache__/` … Python のキャッシュ

### 1-4. ファイルをコミットする

```bash
git add .
git status
```

`git status` で **.env が一覧に出ていないこと**を確認してから、コミットします。

```bash
git commit -m "LINE交通費精算Bot 初回コミット"
```

### 1-5. GitHub にリポジトリを作成する

1. [GitHub](https://github.com/) にログインし、右上の **+** → **New repository** をクリックします。
2. **Repository name** に `line-expense-bot` など好きな名前を付けます。
3. **Public** を選び、**Create repository** を押します。
4. 作成後の画面に表示される「**…or push an existing repository from the command line**」のコマンドをコピーします。例は次のとおりです。

   ```bash
   git remote add origin https://github.com/あなたのユーザー名/line-expense-bot.git
   git branch -M main
   git push -u origin main
   ```

### 1-6. リモートを追加してプッシュする

上記のコマンドを、あなたのリポジトリURLに合わせて実行します。

```bash
git remote add origin https://github.com/あなたのユーザー名/line-expense-bot.git
git branch -M main
git push -u origin main
```

※ すでに `origin` がある場合は `git remote add origin ...` は不要です。別のリモート名を使う場合は `origin` の部分を読み替えてください。

これで GitHub にコードがアップロードされました。以降、Render はこのリポジトリを参照してデプロイします。

---

## 2. 前提の確認

- GitHub にこのリポジトリをプッシュ済みであること（上記で完了）
- [Render](https://render.com/) のアカウントを作成済みであること
- LINE Developers で本番用（または検証用）チャネルの **Channel secret** と **Channel access token** を用意していること

---

## 3. ローカルで動作確認する（Render デプロイ前）

Render にデプロイする前に、同じコードがローカルで問題なく動くことを確認しておくと安心です。ここでは最低限の確認手順をまとめます。詳しいセットアップは **SETUP.md** を参照してください。

### 3-1. 仮想環境とパッケージ

```bash
cd "/Users/shiraishiatsushi/コンテンツ用/課題5-3-2 LINE交通費"
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3-2. 環境変数（.env）の準備

プロジェクトルートに `.env` を作成し、次の内容を設定します。LINE の値は LINE Developers のチャネルから取得します。

```env
LINE_CHANNEL_SECRET=あなたのChannel secret
LINE_CHANNEL_ACCESS_TOKEN=あなたのChannel access token
DATABASE_URL=sqlite:///./line_expense.db
DEFAULT_INVITE_CODE=dev2025
```

※ `.env` は Git にコミットしないでください（.gitignore に含まれています）。

### 3-3. DB の初期化と起動

```bash
python scripts/init_db.py
python run.py
```

次のように表示されれば起動成功です。

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3-4. ブラウザで確認

- http://localhost:8000 を開き、`{"status":"ok",...}` が表示されること
- http://localhost:8000/health を開き、`{"status":"healthy"}` が表示されること

### 3-5. LINE から動作確認（任意）

LINE の Webhook は HTTPS が必須なため、ローカルで LINE からメッセージを受け取るには **ngrok** などでトンネルを張る必要があります。

1. 別ターミナルで `ngrok http 8000` を実行し、表示された `https://xxxx.ngrok-free.app` をコピーする
2. LINE Developers の該当チャネル → **Messaging API** → **Webhook URL** に `https://xxxx.ngrok-free.app/webhook` を設定する
3. LINE で友だち追加し、招待コード → フルネーム（漢字）→ 交通費送信まで試す

ここまで問題なければ、同じコードを Render にデプロイして本番運用に進めます。ngrok での確認を省略する場合は、少なくとも **3-4 のブラウザ確認**まで行ってからデプロイしてください。

---

## 4. Render で PostgreSQL を作成

1. [Render Dashboard](https://dashboard.render.com/) にログインします。
2. **New +** → **PostgreSQL** を選びます。
3. **Name** に `line-expense-db` など好きな名前を付けます。
4. **Region** を選び、**Create Database** を押します。
5. 作成後、**Connections** の **Internal Database URL** をコピーします。  
   形式例：`postgresql://user:pass@host/dbname`

※ Internal は同じRender内のWebサービスから接続する用です。外部から接続する場合は **External Database URL** を使います（ここではWebとDBを同じRender内に置く想定で Internal で問題ありません）。

---

## 5. Web サービスを作成

1. **New +** → **Web Service** を選びます。
2. このリポジトリを連携し、対象リポジトリを選択します。
3. 次のように設定します。

   | 項目 | 値 |
   |------|-----|
   | Name | `line-expense-bot` など |
   | Region | DB と同じリージョン推奨 |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

4. **Advanced** で **Add Environment Variable** を押し、次の環境変数を追加します。

   | Key | Value |
   |-----|--------|
   | `LINE_CHANNEL_SECRET` | あなたの Channel secret |
   | `LINE_CHANNEL_ACCESS_TOKEN` | あなたの Channel access token（長期推奨） |
   | `LINE_ADMIN_USER_ID` | 完了報告を受け取る管理者のLINE user ID（任意） |
   | `DATABASE_URL` | 手順4でコピーした **Internal Database URL** |
   | `DEFAULT_INVITE_CODE` | 本番用招待コード（任意・DBに招待コードを入れる場合は不要） |

   Googleスプレッドシート連携をする場合のみ追加：

   | Key | Value |
   |-----|--------|
   | `GOOGLE_SPREADSHEET_ID` | スプレッドシートID |
   | `GOOGLE_CREDENTIALS_JSON_PATH` | サービスアカウントJSONをペーストする場合は使わず、下記「スプレッドシート連携」を参照 |

5. **Create Web Service** で作成します。
6. ビルドが成功すると、**https://xxxx.onrender.com** のようなURLが発行されます。

---

## 6. データベースの初期化（初回のみ）

Render の Web サービスは起動時に `init_db()` でテーブルを作成します（`app/main.py` の lifespan で実行）。  
そのため、**初回デプロイ後はテーブルは自動作成されます**。

招待コードをDBに登録したい場合は、次のいずれかで行います。

- **A. 環境変数で対応**  
  `DEFAULT_INVITE_CODE` を設定しておけば、DBにレコードがなくてもそのコードで登録できます。追加作業は不要です。

- **B. 手元でスクリプトを実行**  
  手元のPCで `DATABASE_URL` に **External Database URL** を設定し、  
  `python scripts/init_db.py` および  
  `INVITE_CODE=本番用コード python scripts/init_db.py`  
  を実行して招待コードを投入します。  
  （External URL は Render の DB 画面の **Connections** にあります。ネットワーク制限に注意してください。）

---

## 7. LINE Webhook URL の設定

1. LINE Developers の該当チャネルの **Messaging API** を開きます。
2. **Webhook URL** に次のように入力します。  
   `https://あなたのRenderのURL/webhook`  
   例：`https://line-expense-bot.onrender.com/webhook`
3. **Update** を押し、**Use webhook** を **Enabled** にします。
4. **Verify** で成功すれば完了です。

---

## 8. 動作確認（本番）

1. LINE でそのチャネルを友だち追加し、招待コード → フルネーム（漢字）で登録します。
2. 交通費を送信（例：`4/12 渋谷→新宿 220円 稽古`）し、登録・履歴・月別集計・完了ができることを確認します。
3. 管理者通知が必要な場合は、`LINE_ADMIN_USER_ID` を設定し、完了報告が届くか確認します。

---

## 9. Googleスプレッドシート連携（任意）

1. Google Cloud でプロジェクトを作成し、Google Sheets API を有効にします。
2. サービスアカウントを作成し、JSONキーをダウンロードします。
3. そのJSONの内容を1行にまとめた文字列を環境変数で渡す方法もありますが、Render では **Secret File** が使えます。
   - Render の Web サービス → **Environment** → **Secret Files** で、  
     **Filename** に `google-credentials.json`、**Contents** にJSONの内容を貼り付けます。
   - アプリでは `/etc/secrets/google-credentials.json` のようなパスで読むよう、`GOOGLE_CREDENTIALS_JSON_PATH` にそのパスを設定します。  
     （Render の Secret File の実際のパスはドキュメントで確認してください。）
4. 共有するスプレッドシートの「共有」で、サービスアカウントのメールアドレスを編集者として追加します。
5. 環境変数 `GOOGLE_SPREADSHEET_ID` に、スプレッドシートのID（URLの `/d/` と `/edit` の間）を設定します。
6. デプロイ後、Botで交通費を登録・完了すると、スプレッドシートに書き出されます（`sync_all_expenses` が完了時に呼ばれます）。

---

## 10. render.yaml を使う場合

リポジトリに `render.yaml` を置いている場合、Render の **Blueprint** で一括作成できます。

1. Dashboard で **New +** → **Blueprint** を選び、リポジトリを指定します。
2. `render.yaml` が読み込まれ、Web サービスと PostgreSQL の作成内容が表示されます。
3. 環境変数（`LINE_CHANNEL_SECRET` など）は **Dashboard の該当サービス** で手動設定してください。`render.yaml` の `sync: false` は「シークレットは手動で設定」の意味です。
4. データベースの **Internal Database URL** を、Web サービスの `DATABASE_URL` に設定します（Blueprint でリンクされる場合もあります）。

---

## 環境変数一覧（本番）

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `LINE_CHANNEL_SECRET` | ○ | LINE Channel secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | ○ | LINE Channel access token（長期推奨） |
| `LINE_ADMIN_USER_ID` | - | 完了報告を受け取る管理者の user ID |
| `DATABASE_URL` | ○ | Render の Internal Database URL（PostgreSQL） |
| `DEFAULT_INVITE_CODE` | - | 招待コードをDBで管理しない場合のデフォルト |
| `GOOGLE_CREDENTIALS_JSON_PATH` | - | スプレッドシート用サービスアカウントJSONのパス |
| `GOOGLE_SPREADSHEET_ID` | - | 出力先スプレッドシートID |

---

以上で、Render へのデプロイとLINE Webhookの本番設定は完了です。
