# SGC プロジェクト HANDOFF

## 最終更新
2026-04-11

---

## 今日やったこと

- **ニュースカテゴリ変更**（`news.html`、コミット `8f6092c`）:
  - タブ構成を「すべて・SGC・大黄金展・金相場・プラチナ」→「すべて・SGCホール・黄金泥棒・大黄金展・金相場（関連）」に変更
  - 「すべて」の検索クエリに全カテゴリのキーワードを統合
  - 「黄金泥棒（映画）」バッジを追加
  - 記事を更新日降順（新しい順）にソートするよう修正

- **UX改善**（`main.html` / `index.html`、コミット `51c50d0`）:
  - `main.html`: 価格帯ヘッダーに「更新」ボタンを追加（価格・大黄金展データを再fetch）
  - `main.html`: `quick-btn` 等に `touch-action: manipulation` を追加（タップ300ms遅延除去）
  - `index.html`: ナビ・ボトムナビに `touch-action: manipulation` を追加
  - `index.html`: GASページ等タップ時にローディングオーバーレイ（スピナー）を表示、iframe load完了で自動非表示

---

## 次にやること（TODO）

- [ ] スマホ実機で PWA インストール後の動作確認（ボトムナビ・セーフエリア・オフライン）
- [ ] PWA バナーのアイコン画像が外部URL（`raw.githubusercontent.com`）のまま → ローカル参照に変更検討
- [ ] `data/tanaka_price.json` などの更新を Service Worker が正しくリアルタイム反映するか確認
- [ ] `scripts/check_tanaka_update(使わなければ削除する).py` の整理判断
- [ ] ニュースカテゴリの検索クエリ（特にSGCホール）が意図した記事を取得できるか実機確認

---

## 現在のデプロイ状況

- **GitHub Pages**: `https://sgc-gold.github.io/sgc/`
- **最新コミット**: `51c50d0` (2026-04-11)
- **ブランチ**: `main`

---

## セッションログ

<!-- Stop フックが自動管理 -->
