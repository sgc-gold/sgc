import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

# 日本語ページから取得
URL = "https://gold.tanaka.co.jp/commodity/souba/index.php"

# 保存先
PATH_MAIN = "data/tanaka_price.json"
PATH_930 = "data/tanaka_price_930.json"

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

    # 公表時刻を取得
    update_time_raw = soup.select_one("h3 span").text.strip()
    return prices, update_time_raw


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def main():
    now = datetime.now().strftime("%H:%M")
    prices, update_text = fetch_tanaka_prices()

    # 9:30 の場合 → 保存
    if now.startswith("09:3"):
        data = {
            "update_time": update_text,
            "prices": prices
        }
        save_json(PATH_MAIN, data)
        save_json(PATH_930, data)
        print("✅ 9:30 更新データを保存しました")

    # 14:00 の場合 → 9:30比を算出
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

                    # 符号付きフォーマット（＋−付き、千区切りなし、整数 or 小数対応）
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
        print("⏸ 現在は定刻外です（実行なし）")


if __name__ == "__main__":
    main()
