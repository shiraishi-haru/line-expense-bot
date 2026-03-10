# 初心者向けセットアップ手順（LINE交通費精算Bot）

このドキュメントでは、開発PCでBotを動かすまでを順に説明します。

---

## 1. 必要なもの

- **Python 3.10 以上**（3.11 推奨）
- **LINE公式アカウント**（LINE Developers でチャネル作成）
- **ngrok**（ローカルをHTTPSで公開するため・無料で可）

---

## 2. リポジトリの準備

ターミナルを開き、プロジェクトフォルダに移動します。

```bash
cd "/Users/shiraishiatsushi/コンテンツ用/課題5-3-2 LINE交通費"
```

（パスはお使いの環境に合わせて変更してください。）

---

## 3. 仮想環境の作成と有効化

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows（コマンドプロンプト）

```bash
python -m venv venv
venv\Scripts\activate
```

プロンプトの先頭に `(venv)` と出ればOKです。

---

## 4. パッケージのインストール

```bash
pip install -r requirements.txt
```

---

## 5. LINE Developers でチャネルを作成

1. [LINE Developers](https://developers.line.biz/) にログインします。
2. **Create** で新しいプロバイダー（例：会社名）を作成します。
3. **Create a Messaging API channel** でチャネルを作成します。
4. チャネルができたら、**Basic settings** の「Channel secret」をコピーします。
5. **Messaging API** タブの「Channel access token」でトークンを発行し、コピーします。

※ 本番では「Channel access token」の長期トークンを発行して利用してください。

---

## 6. 環境変数ファイルの作成

プロジェクトのルートに `.env` ファイルを作成します。

1. `.env.example` をコピーして `.env` という名前で保存します。

   ```bash
   cp .env.example .env
   ```

2. `.env` を開き、次の値を書き換えます。

   - `LINE_CHANNEL_SECRET` … 先ほどコピーした Channel secret
   - `LINE_CHANNEL_ACCESS_TOKEN` … 先ほどコピーした Channel access token
   - （任意）`DEFAULT_INVITE_CODE` … 初回登録で使う招待コード（例：`dev2025`）

   ```env
   LINE_CHANNEL_SECRET=あなたのChannel secret
   LINE_CHANNEL_ACCESS_TOKEN=あなたのChannel access token
   DEFAULT_INVITE_CODE=dev2025
   DATABASE_URL=sqlite:///./line_expense.db
   ```

---

## 7. データベースの初期化

テーブルを作成し、必要なら招待コードを1件追加します。

```bash
python scripts/init_db.py
```

招待コードを追加する場合（例：`mycode`）：

```bash
INVITE_CODE=mycode python scripts/init_db.py
```

`.env` の `DEFAULT_INVITE_CODE` を設定している場合は、DBにコードがなくてもその値で登録できます。

---

## 8. アプリの起動

```bash
python run.py
```

次のように表示されれば起動成功です。

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

ブラウザで http://localhost:8000 を開き、`{"status":"ok",...}` が表示されればOKです。

---

## 9. ngrok で HTTPS 公開（LINE Webhook 用）

LINE の Webhook は HTTPS のURLが必須です。ローカルを ngrok で公開します。

1. [ngrok](https://ngrok.com/) のサイトから ngrok をダウンロード・インストールします。
2. 別のターミナルで、アプリを起動したまま次を実行します。

   ```bash
   ngrok http 8000
   ```

3. 表示された **https://xxxx.ngrok-free.app** のようなURLをコピーします。

**固定URLで運用したい場合**は、ngrok ではなく **Render などの外部サーバーにデプロイ**すると、URLが変わらず便利です。手順は **DEPLOY.md** を参照してください。

---

## 10. LINE に Webhook URL を設定

1. LINE Developers の該当チャネルの **Messaging API** タブを開きます。
2. **Webhook URL** に次のように入力します。  
   `https://あなたのngrokのURL/webhook`  
   例：`https://abcd1234.ngrok-free.app/webhook`
3. **Update** を押して保存します。
4. **Webhook settings** の「Use webhook」を **Enabled** にします。
5. 「Verify」を押し、成功すれば設定完了です。

---

## 11. 動作確認

1. LINE でそのチャネルの公式アカウントを友だち追加します（QRコードはチャネルの「Basic settings」にあります）。
2. 何かメッセージを送ると、「招待コードを入力してください。」と返ってくれば、登録フローに入っています。
3. `.env` の `DEFAULT_INVITE_CODE`（例：`dev2025`）を入力します。
4. 次に「フルネームを漢字で入力してください」と出たら、漢字の名前（例：白石温）を入力します。
5. 「登録が完了しました」と表示されれば登録完了です。
6. 交通費を送信してみます。  
   例：`4/12 渋谷→新宿 220円 稽古`  
   「交通費を登録しました」と返ってくればOKです。
7. 「履歴確認」「月別集計」「完了」も送って動作を確認できます。

---

## 12. 管理者への完了通知について

「完了」送信時に、管理者のLINE個人アカウントに通知を送るには、**管理者のLINE user ID**（`U` で始まる33文字程度の長い文字列）を `.env` に設定します。

1. **管理者本人**が、このBotを友だち追加したアカウントで、Botに「**マイID**」と送信します。
2. Botが返す **あなたのLINE user ID**（`U` で始まる長い英数字）をコピーします。
3. `.env` の `LINE_ADMIN_USER_ID=` の右に、**その文字列だけ**を貼り付け保存します。数字だけの短い値（例: 19072244）は無効です。
4. `python run.py` を再起動します。

これで「完了」送信時に、そのIDのアカウントに通知が届きます。**自分で「完了」を送った場合でも、LINE_ADMIN_USER_ID が正しければ管理者のトークに通知が届きます。**

---

## トラブルシューティング

- **管理者通知が届かない**  
  `.env` の `LINE_ADMIN_USER_ID` には、**LINEの user ID**（`U` で始まる33文字程度の長い文字列）を設定する必要があります。数字だけの短い値（例: 19072244）では送信できません。管理者がBotに「**マイID**」と送り、表示された `U` で始まるIDをコピーして `.env` に設定してください。設定後はサーバーを再起動します。

- **「ボットサーバーから200以外のHTTPステータスコードが返されました。(400 Bad Request)」**  
  LINE が Webhook を送ったときに、サーバーが 400 を返しています。**ほぼすべて「署名が合わない」ことが原因**です。  
  1. **Channel secret の確認**  
     LINE Developers → 該当チャネルの **Basic settings** → **Channel secret** をコピーし、`.env` の `LINE_CHANNEL_SECRET` と**完全に一致**しているか確認してください。前後にスペースや改行が入っていないか、別チャネルの値になっていないかも確認します。  
  2. **.env が読み込まれているか**  
     `python run.py` は**プロジェクトのルート**（`requirements.txt` や `.env` があるフォルダ）で実行してください。別のフォルダから実行すると `.env` が読まれず、署名検証に失敗します。  
  3. **サーバーを再起動**  
     `.env` を書き換えたあとは、必ず `python run.py` を止めてから再度起動してください。  
  4. **ログで原因を確認**  
     ターミナルに `Webhook: Invalid signature...` や `Webhook: Missing X-Line-Signature` が出ていないか確認します。出ていれば、上記の Channel secret と実行場所を再度確認してください。

- **「Invalid signature」が出る**  
  `.env` の `LINE_CHANNEL_SECRET` が正しいか、環境変数が読み込まれているか確認してください。`python run.py` はプロジェクトルートで実行してください。

- **「招待コードが正しくありません」**  
  `DEFAULT_INVITE_CODE` を設定している場合はその文字列を、DBに投入した場合はそのコードを、余分なスペースなしで入力してください。

- **交通費が登録されない**  
  形式を守って送信してください。例：`4/12 渋谷→新宿 220円 稽古`（日付、出発→到着、金額円、用途）。

- **ngrok のURLが変わる / 固定URLで使いたい**  
  無料版の ngrok では起動のたびにURLが変わるため、その都度 LINE Developers の Webhook URL を更新する必要があります。  
  **固定URLで運用したい場合は、外部サーバーにデプロイする方法があります。** 本プロジェクトでは **Render** へのデプロイ手順を **DEPLOY.md** にまとめています。Render にデプロイすると `https://あなたのサービス名.onrender.com/webhook` のような固定URLが発行され、LINE の Webhook URL を一度設定すれば変更不要です。そのほか、Heroku・AWS・GCP・VPS などにデプロイしても同様に固定URLで利用できます。

---

以上で、初心者向けセットアップは完了です。本番デプロイは **DEPLOY.md** を参照してください。
