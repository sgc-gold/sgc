import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
import sys

# ================================
# GitHub Actionsでの手動実行判定
# workflow_dispatchなら常に実行
# ================================
is_workflow_dispatch = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

if not is_workflow_dispatch:
    now = datetime.now()
    if not ((now.hour == 9 and now.minute >= 35 and now.minute <= 45) or
            (now.hour == 14 and now.minute >= 5 and now.minute <= 15)):
        print("⏸ 定刻外のためスキップ（スケジュール実行）")
        sys.exit(0)
else:
    print("🚀 手動実行モード（定刻外でも強制実行）")

# ================================
# 取得対象URL
# ================================
URL = "https://gold.tanaka.co.jp/commodity/souba/index.php"

# 保存先
PATH_MAIN = "data/tanaka_price.json"
PATH_930 = "data/tanaka_price_930.json"

# ================================
# 金額取得関数
# ================================
def fetch_tanaka_prices():
    res = requests.get(URL)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

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

    # 公表時刻
    update_time_raw = soup.select_one("h3 span").text.strip()
    return prices, update_time_raw

# ================================
# JSON保存・読み込み
# ================================
def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# ================================
# メイン処理
# ================================
def main():
    now = datetime.now().strftime("%H:%M")
    prices, update_text = fetch_tanaka_prices()

    # -------------------------------
    # 手動実行時：常に更新を実行
    # -------------------------------
    if is_workflow_dispatch:
        data = {
            "update_time": update_text,
            "prices": prices
        }
        save_json(PATH_MAIN, data)
        print("✅ 手動実行モードでデータを保存しました")
        return

    # -------------------------------
    # 9:30 の場合 → 保存
    # -------------------------------
    if now.startswith("09:3"):
        data = {
            "update_time": update_text,
            "prices": prices
        }
        save_json(PATH_MAIN, data)
        save_json(PATH_930, data)
        print("✅ 9:30 更新データを保存しました")

    # -------------------------------
    # 14:00 の場合 → 9:30比を算出
    # -------------------------------
    elif now.startswith("14:0"):
        morning_data = load_json(PATH_930)
        if morning_data:
            for metal in prices:
                try:
                    curr_retail = float(prices[metal]["retail"].replace(",", ""))
                    curr_buy = float(prices[metal]["buy"].replace(",", ""))
                    morn_retail = float(morning_data["prices"][metal]["retail"].replace(",", ""))
                    morn_buy = float(morning_data["prices"][metal]["buy"].replace(",", ""))

                    retail_diff930 = curr_retail - morn_retail
                    buy_diff930 = curr_buy - morn_buy

                    prices[metal]["retail_930diff"] = f"{retail_diff930:+,.2f}".rstrip("0").rstrip(".") + " 円"
                    prices[metal]["buy_930diff"] = f"{buy_diff930:+,.2f}".rstrip("0").rstrip(".") + " 円"
                except Exception:
                    prices[metal]["retail_930diff"] = ""
                    prices[metal]["buy_930diff"] = ""
        else:
            for metal in prices:
                prices[metal]["retail_930diff"] = ""
                prices[metal]["buy_930diff"] = ""

        data = {
            "update_time": update_text,
            "prices": prices
        }
        save_json(PATH_MAIN, data)
        print("✅ 14:00 更新データを保存しました（9:30比込み）")

    else:
        print("⏸ 現在は定刻外です（スケジュール実行時のみ）")


if __name__ == "__main__":
    main()
