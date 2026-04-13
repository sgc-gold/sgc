# SGC プロジェクト HANDOFF

## 最終更新
2026-04-13

---

## 今日やったこと

- **`.github/workflows/update_tanaka.yml` 修正**: 価格更新後に `deploy.yml` を明示的にトリガーするよう修正（gh-pages 反映漏れ対応）
- **HANDOFF.md 更新**: セッション終了処理
- commit & push 完了（コミット `65cf028`）

---

## 次にやること（TODO）

- [ ] スマホ実機で PWA インストール後の動作確認（ボトムナビ・セーフエリア・オフライン）
- [ ] PWA バナーのアイコン画像が外部URL（`raw.githubusercontent.com`）のまま → ローカル参照に変更検討
- [ ] `data/tanaka_price.json` などの更新を Service Worker が正しくリアルタイム反映するか確認
- [ ] `scripts/check_tanaka_update(使わなければ削除する).py` の整理判断
- [ ] ニュースカテゴリの検索クエリ（特にSGCホール）が意図した記事を取得できるか実機確認
- [ ] `update_tanaka.yml` のトリガー修正が実際に gh-pages へ正しく反映されるか動作確認

---

## 現在のデプロイ状況

- **GitHub Pages**: `https://sgc-gold.github.io/sgc/`
- **最新コミット**: `65cf028` (2026-04-13)
- **ブランチ**: `main`

---

## セッションログ

<!-- Stop フックが自動管理 -->
