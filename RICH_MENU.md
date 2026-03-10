# リッチメニュー設定（LINE交通費精算Bot）

LINE公式アカウントのリッチメニューで、以下の4つのボタンを表示する設定手順です。

---

## ボタンとポストバック

| 表示テキスト     | ポストバック data    | 動作           |
|------------------|----------------------|----------------|
| 交通費入力方法   | `action=input_guide`  | 入力例を返す   |
| 履歴確認         | `action=history`      | 履歴一覧を返す |
| 月別集計         | `action=monthly`      | 今月の集計を返す |
| 完了報告         | `action=complete`    | 完了処理＋管理者通知 |

---

## 設定手順（LINE Developers）

1. [LINE Developers](https://developers.line.biz/) で該当チャネルを開く。
2. **Messaging API** タブの **Rich menu** を開く。
3. **Create** でリッチメニューを作成する。
4. **Action** を各エリアに設定する：
   - **Action type**: Postback
   - **Postback data**: 上表の `action=xxx` をそのまま入力（例: `action=input_guide`）
5. 画像（推奨サイズ 2500x1686 または 2500x843）をアップロードする。
6. 作成したリッチメニューを **Default** に設定するか、必要に応じて時間帯で切り替える。

※ リッチメニューは Bot 側で API から作成することもできます（line-bot-sdk や LINE Messaging API の Rich Menu 作成 API を利用）。

---

## 動作確認

友だち追加後、画面下部にリッチメニューが表示されます。各ボタンをタップすると、上記のポストバックが送信され、Bot が対応する返信をします。
