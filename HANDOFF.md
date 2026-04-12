# SGC プロジェクト HANDOFF

## 最終更新
2026-04-12

---

## 今日やったこと

- **YouTube 短尺動画フィルターを追加**（コミット `0270810`）:
  - 検索結果に表示される数秒の変な動画（ショート等）を除外
  - `videos.list` APIでdurationを取得し、20秒未満の動画を非表示にする処理を追加
  - `parseDurationSec()` 関数でISO 8601 durationを秒数に変換

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
- **最新コミット**: `0270810` (2026-04-12)
- **ブランチ**: `main`

---

## セッションログ

<!-- Stop フックが自動管理 -->
