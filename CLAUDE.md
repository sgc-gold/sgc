# SGC プロジェクト — CLAUDE.md

## プロジェクト概要
(株)SGC横森の社内ポータル PWA。田中貴金属の金・プラチナ・銀の価格を自動取得し、メール・LINE WORKS で通知するシステム。

GitHub Pages でホスト: `https://sgc-gold.github.io/sgc/`

---

## ファイル構成

```
sgc/
├── index.html          # PWA エントリ（ログイン）
├── main.html           # ダッシュボード
├── price.html          # 貴金属価格表示
├── market.html         # 市場情報
├── diamond.html        # ダイヤモンド
├── gemstone.html       # 宝石
├── coin.html           # コイン
├── register.html       # 登録
├── schedule.html       # スケジュール
├── contacts.html       # 連絡先
├── news.html           # ニュース
├── youtube.html        # YouTube
├── manifest.json       # PWA マニフェスト
├── sw.js               # Service Worker
├── data/
│   ├── tanaka_price.json      # 最新の田中貴金属価格（9:30 / 14:00）
│   ├── tanaka_price_930.json  # 当日 9:30 価格（14:00 比較用）
│   ├── exchange_rate.json     # USD/JPY レート
│   ├── history/               # 日付別価格履歴 (YYYY-MM-DD.json)
│   ├── diamonds.json / gemstones.json / coins.json
│   ├── rapaport.json / calibrations.json / cuts.json / models.json
│   └── exhibition.json
├── scripts/
│   ├── update_tanaka.py       # 田中貴金属スクレイピング → data/*.json 更新
│   ├── tanaka.py              # メール(SendGrid) + LINE WORKS 送信
│   ├── comment.py             # 9:30 市況コメント取得
│   ├── comment_pm.py          # 14:00 市況コメント取得
│   ├── BullionVault.py        # BullionVault チャート画像キャプチャ（Selenium）
│   ├── gaitame_usdjpy.py      # ドル円チャート画像キャプチャ
│   ├── fetch_exchange.js      # USD/JPY レート取得（Node.js）
│   └── register.js            # フロントエンド登録処理
└── .github/workflows/
    ├── update_tanaka.yml      # GAS → repository_dispatch → 価格更新 → 通知トリガー
    ├── tanaka_notify.yml      # チャート取得 → メール＋LINE WORKS 送信
    └── update_exchange.yml    # 毎日 9:00 JST に USD/JPY レート更新
```

---

## 自動化フロー

```
GAS（Google Apps Script）
  └─ repository_dispatch → update_tanaka.yml
        ├─ update_tanaka.py 実行（価格データを data/*.json に保存）
        ├─ git commit & push
        └─ repository_dispatch → tanaka_notify.yml
              ├─ comment.py / comment_pm.py（市況コメント取得）
              ├─ BullionVault.py（チャート画像）
              ├─ gaitame_usdjpy.py（ドル円チャート）
              └─ tanaka.py（メール + LINE WORKS 送信）

update_exchange.yml: cron 毎日 0:00 UTC（9:00 JST）
  └─ fetch_exchange.js → data/exchange_rate.json 更新
```

---

## 価格データ仕様

### `data/tanaka_price.json`
```json
{
  "update_time": "2026年XX月XX日 09:30公表（日本時間）",
  "prices": {
    "GOLD":     { "retail": "15,000", "retail_diff": "+100", "buy": "14,200", "buy_diff": "+100", "retail_930diff": "", "buy_930diff": "" },
    "PLATINUM": { ... },
    "SILVER":   { ... }
  }
}
```
- `retail_930diff` / `buy_930diff`: 14:00 更新時のみ付与（9:30 比）

### `data/tanaka_price_930.json`
当日 9:30 時点のスナップショット。14:00 の差分計算に使用。

### `data/history/YYYY-MM-DD.json`
```json
{ "date": "2026-03-02", "snapshots": [ { "update_time": "...", "prices": { ... } } ] }
```

---

## 通知設定（secrets）

| Secret | 用途 |
|--------|------|
| `TANAKA_GITHUB_TOKEN` | GitHub PAT（push / dispatch） |
| `SENDGRID_API_KEY` | SendGrid メール送信 |
| `LINEWORKS_WEBHOOK_URL` | LINE WORKS Webhook |

- 送信元: `yokomori@sgc-gold.co.jp`
- 宛先: `yokomori@sgc-gold.co.jp`、BCC: `s.forest.1127@gmail.com`

---

## スプレッド基準値

| 金属 | デフォルトスプレッド（税抜） |
|------|--------------------------|
| 金 | 325 円 |
| プラチナ | 385 円 |
| 銀 | 15.5 円 |

スプレッドが変わった場合、メール件名に「※スプレッド変更」が付与され LINE WORKS でも警告。

---

## 開発上の注意

- `.env` や secrets は絶対に読まない・コードに含めない
- `data/*.json` は GitHub Actions が自動更新するため手動編集しない
- HTML は純粋な JavaScript + CSS（フレームワーク不使用）
- PWA 対応: `manifest.json` + `sw.js` でオフラインキャッシュあり
- GitHub Pages から直接 `data/*.json` を fetch してフロントで表示
- `scripts/` の Python スクリプトはローカルでは通常実行しない（GitHub Actions 環境前提）
