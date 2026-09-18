# ダイヤ相場データの業者フィールド

`data/diamonds_YYYY.json` の各レコードで、業者は英語フィールド名 `vendor` に記録する。

| `vendor` の値 | 画面表示 |
| --- | --- |
| `NJ` | NJ |
| `MONOBANK` | ものばんく |

新規データには必ず `vendor` を指定する。ものばんくのレコードには `"vendor":"MONOBANK"`、NJのレコードには `"vendor":"NJ"` を追加する。

過去に作成された `vendor` のないレコードは、検索画面では `NJ` として扱う。`vendor` を省略して新しいものばんくのレコードを追加すると NJ と判定される。検索対象は認証済みポータル内の `data/diamonds_YYYY.json`。
