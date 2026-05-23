# Cloudflare Pages 移行現状メモ

作成日: 2026-05-22

## 現在の最優先

GitHub Pages 本番を壊さず、Cloudflare Pages を安全に並行運用する。

まずは Cloudflare Pages を「外部から見えない状態」にすることを優先する。社員ログインは Cloudflare Access + LINE WORKS SSO を主認証とし、会社メールアドレス OTP を fallback として残す。

## 現在の方針

- 2026年6月末までは GitHub Pages 本番を継続運用する。
- Cloudflare Pages は検証・段階移行用として使用する。
- GitHub Pages を即停止しない。
- `deploy.yml` を削除しない。
- `gh-pages` を削除しない。
- repo private 化しない。
- GAS はまだ変更しない。
- `raw.githubusercontent.com` 参照はまだ整理しない。
- `sw.js` は原則現状維持する。
- 6月中は GitHub Pages 本番と Cloudflare Pages 検証を並行運用する。
- Custom Domain は使わず、`pages.dev` URL を継続使用する。

## 現在の本番

GitHub Pages 本番:

```text
https://sgc-gold.github.io/sgc/
```

これは 2026年6月末までは正式本番として維持する。

## Cloudflare Pages 検証環境

Cloudflare Pages:

```text
https://sgc-internal-portal.pages.dev/
```

## Cloudflare Pages 設定

```text
Framework preset: None
Build command: npm run build:portal
Build output directory: dist-portal
Root directory: 空欄
Production branch: main
```

## dist-portal 構成

Cloudflare Pages 側では repo root を直接公開しない。`npm run build:portal` で `dist-portal/` に許可したファイルだけを出力する。

公開対象:

```text
index.html
main.html
price.html
diamond.html
gemstone.html
coin.html
schedule.html
contacts.html
news.html
youtube.html
register.html
market.html
portal-frame-bridge.js
sw.js
manifest.json
image/
data/
```

公開しないもの:

```text
scripts/
gas/
.github/
tools/
package.json
package-lock.json
.env
wrangler.toml
wrangler.jsonc
*.py
*.ps1
*.txt
*.log
```

## diamonds.json

`data/diamonds.json` は Cloudflare Workers の 25MiB 制限問題のため、Cloudflare Pages 成果物から除外済み。

`diamond.html` / `sw.js` は以下を参照している:

```text
diamonds_2025.json
diamonds_2026.json
rapaport.json
exchange_rate.json
```

## Cloudflare Pages Functions

`functions/_middleware.js` を使用する。

役割:

- 危険パスの 404 化

Basic 認証は Cloudflare Access への移行に合わせて廃止する。ロールバック用に旧 middleware は以下へ退避する。

```text
docs/cloudflare/_middleware.basic-auth.backup.js
```

`BASIC_AUTH_USER` / `BASIC_AUTH_PASS` はロールバック用として Cloudflare Pages Secrets に残してよいが、通常運用では使用しない。

## Cloudflare Access 認証方針

主認証:

```text
LINE WORKS SAML
```

fallback:

```text
One-time PIN
```

OTP 許可対象:

```text
@sgc-gold.co.jp
```

Access Application:

```text
Type: Self-hosted
Domain: sgc-internal-portal.pages.dev
Path: /*
Session duration: 7 days
Identity providers: LINE WORKS SAML, One-time PIN
Instant authentication: OFF
```

Access Policy:

```text
Allow LINE WORKS SSO
- Action: Allow
- Include: Emails ending in @sgc-gold.co.jp
- Require: Login Methods = LINE WORKS SAML
- Session duration: 7 days

Allow Company Email OTP Fallback
- Action: Allow
- Include: Emails ending in @sgc-gold.co.jp
- Require: Login Methods = One-time PIN
- Session duration: 24 hours
```

使用しない:

```text
Bypass
Everyone
All valid emails
Custom Domain
```

LINE WORKS SAML 側の想定:

```text
ACS URL: https://<team-name>.cloudflareaccess.com/cdn-cgi/access/callback
SP Entity ID: https://<team-name>.cloudflareaccess.com/cdn-cgi/access/callback
Cloudflare metadata: https://<team-name>.cloudflareaccess.com/cdn-cgi/access/saml-metadata
Name ID format: emailAddress
Name ID value: 会社メールアドレス
Attribute email: 会社メールアドレス
Attribute name: 表示名
Attribute groups: 利用可能なら部署/グループ
```

## _routes.json

`tools/build-portal.mjs` で `dist-portal/_routes.json` を生成する。

内容:

```json
{
  "version": 1,
  "include": ["/*"],
  "exclude": []
}
```

全ルートを Pages Functions に通す。

## middleware の現在仕様

- 危険パス: `404`
- その他: Cloudflare Access 認証後に `context.next()`

404 対象:

```text
/scripts
/.github
/gas
/tools
/data/diamonds.json
/package.json
/package-lock.json
/wrangler.toml
/wrangler.jsonc
/.env
```

## 現在の確認済み状態

未ログイン:

```text
https://sgc-internal-portal.pages.dev/
-> Cloudflare Access ログイン画面
-> LINE WORKS SSO または会社メール OTP
```

ログイン後:

```text
/ -> 200
/scripts/register.js -> 404
/.github/workflows/deploy.yml -> 404
/data/diamonds.json -> 404
/data/diamonds_2026.json -> 200
```

つまり、以下は確認済み。

- Cloudflare Access 認証後の表示
- `dist-portal` 成功
- 危険ファイル非公開成功
- 必要 JSON のみ認証後公開

## Cloudflare Custom Domain

`portal.sgc-gold.co.jp` は一旦保留。

理由:

- DNS 管理権限の確認待ち。
- 管理者確認未実施。
- まずは `pages.dev` で安定運用を優先する。

## 今後の予定

まずは `pages.dev` で管理者・一部社員テストを行う。

確認対象:

- iPhone
- PWA
- GAS iframe
- ログイン維持
- 画面崩れ
- JSON 取得
- 更新反映

Custom Domain は使わず、`pages.dev` URL のまま運用を継続する。

## ロールバック

LINE WORKS SSO または Access 設定に問題が出た場合は、Basic 認証へ一時的に戻す。

手順:

```text
1. Cloudflare Access Application を一時 disable、または管理者だけ許可に絞る。
2. docs/cloudflare/_middleware.basic-auth.backup.js を functions/_middleware.js に戻す。
3. BASIC_AUTH_USER / BASIC_AUTH_PASS が Pages Secrets に残っていることを確認する。
4. npm run build:portal を確認する。
5. commit / push して Cloudflare Pages を再デプロイする。
```

Access 側の設定は削除せず、disable に留める。

## まだやらないこと

- GitHub Pages 停止
- `deploy.yml` 削除
- `gh-pages` 削除
- repo private 化
- `raw.githubusercontent.com` 整理
- GAS 変更
- `sw.js` 変更
- 社員番号ログイン
- 社員全体展開
- Custom Domain 切替
