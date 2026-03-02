import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
import sys

URL = "https://gold.tanaka.co.jp/commodity/souba/index.php"
PATH_MAIN = "data/tanaka_price.json"
PATH_930 = "data/tanaka_price_930.json"

# 手動実行判定
is_workflow_dispatch = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

def fetch_tanaka_prices():
    res = requests.get(URL)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    prices = {}
    for metal, cls in [("GOLD", "gold"), ("PLATINUM", "pt"), ("SILVER", "silver")]:
        retail = soup.select_one(f"tr.{cls} td.retail_tax").text.strip().replace(" 円", "")
        retail_diff = soup.select_one(f"tr.{cls} td.retail_ratio").text.strip().replace(" 円", "")
        buy = soup.select_one(f"tr.{cls} td.purchase_tax").text.strip().replace(" 円", "")
        buy_diff = soup.select_one(f"tr.{cls} td.purchase_ratio").text.strip().replace(" 円", "")
        prices[metal] = {
            "retail": retail,
            "retail_diff": retail_diff,
            "buy": buy,
            "buy_diff": buy_diff
        }

    update_time_raw = soup.select_one("h3 span").text.strip()
    return prices, update_time_raw

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def main():
    prices, update_text = fetch_tanaka_prices()
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    print(f"🕒 現在時刻: {current_time}")
    print(f"📅 取得データの公表時刻: {update_text}")

    # ※ スキップ判定を削除
    # check_tanaka_update.py がハッシュ変化を確認済みのためここでの重複チェックは不要。
    # ただしサーバーのキャッシュ等で古いデータが返ってくる場合があるため、
    # 既存データと同じ公表時刻の場合は警告を出しつつも処理を継続する。
    existing_data = load_json(PATH_MAIN)
    last_update_time = existing_data["update_time"] if existing_data else None

    if not is_workflow_dispatch and update_text == last_update_time:
        print("⚠ 取得した公表時刻が既存データと同じです（サーバーキャッシュの可能性）。処理を継続します。")

    # === 9:30更新処理 ===
    if "09:30" in update_text:
        data = {"update_time": update_text, "prices": prices}
        save_json(PATH_MAIN, data)
        save_json(PATH_930, data)
        print("✅ 9:30データ保存完了")

    # === 9:30以外の更新（14:00やその他） ===
    else:
        morning_data = load_json(PATH_930)
        if morning_data:
            for metal in prices:
                try:
                    curr_retail = float(prices[metal]["retail"].replace(",", ""))
                    curr_buy = float(prices[metal]["buy"].replace(",", ""))
                    morn_retail = float(morning_data["prices"][metal]["retail"].replace(",", ""))
                    morn_buy = float(morning_data["prices"][metal]["buy"].replace(",", ""))
                    prices[metal]["retail_930diff"] = f"{curr_retail - morn_retail:+,.2f}".rstrip("0").rstrip(".")
                    prices[metal]["buy_930diff"] = f"{curr_buy - morn_buy:+,.2f}".rstrip("0").rstrip(".")
                except Exception as e:
                    print(f"⚠ 差分計算エラー: {metal} - {e}")
                    prices[metal]["retail_930diff"] = ""
                    prices[metal]["buy_930diff"] = ""
        else:
            print("⚠ 9:30データが存在しません → 差分なしで保存")

        data = {"update_time": update_text, "prices": prices}
        save_json(PATH_MAIN, data)
        print(f"✅ {update_text} データ保存完了（9:30比込み）")

    print("💾 保存完了:", PATH_MAIN)

if __name__ == "__main__":
    main()
