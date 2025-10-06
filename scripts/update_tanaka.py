import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

SAVE_PATH = "data/tanaka_price.json"
MORNING_PATH = "data/tanaka_price_0930.json"
BASE_URL = "https://gold.tanaka.co.jp/commodity/souba/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_prices():
    """田中貴金属から価格情報を取得"""
    res = requests.get(BASE_URL, headers=HEADERS)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    metals = ["GOLD", "PLATINUM", "SILVER"]
    table = soup.select_one("table.tbl-data01")
    rows = table.select("tr")

    result = {}
    for metal, row in zip(metals, rows[1:]):
        cols = [c.get_text(strip=True) for c in row.select("td")]
        retail = cols[1].replace("円", "").strip()
        retail_diff = cols[2].replace("円", "").strip()
        buy = cols[4].replace("円", "").strip()
        buy_diff = cols[5].replace("円", "").strip()
        result[metal] = {
            "retail": retail,
            "retail_diff": retail_diff,
            "buy": buy,
            "buy_diff": buy_diff
        }
    return result

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def format_diff(v1, v2):
    """差分をフォーマットして返す"""
    try:
        n1 = int(v1.replace(",", ""))
        n2 = int(v2.replace(",", ""))
        diff = n2 - n1
        sign = "+" if diff > 0 else ""
        return f"{sign}{diff:,}"
    except:
        return "N/A"

def main():
    now = datetime.now()
    hour, minute = now.hour, now.minute

    prices = fetch_prices()

    data = {
        "update_time": now.strftime("%Y-%m-%d %H:%M"),
        "prices": prices
    }

    # --- 9時台なら朝データ保存のみ ---
    if 9 <= hour < 10:
        save_json(prices, MORNING_PATH)
        save_json(data, SAVE_PATH)
        print("✅ 9:30 データ保存完了")
        return

    # --- 14時台なら9:30比も算出 ---
    if 14 <= hour < 15:
        morning = load_json(MORNING_PATH)
        if morning:
            for metal in prices:
                try:
                    prices[metal]["retail_diff0930"] = format_diff(
                        morning[metal]["retail"], prices[metal]["retail"])
                    prices[metal]["buy_diff0930"] = format_diff(
                        morning[metal]["buy"], prices[metal]["buy"])
                except:
                    prices[metal]["retail_diff0930"] = "N/A"
                    prices[metal]["buy_diff0930"] = "N/A"
        else:
            for metal in prices:
                prices[metal]["retail_diff0930"] = "-"
                prices[metal]["buy_diff0930"] = "-"

        data["prices"] = prices
        save_json(data, SAVE_PATH)
        print("✅ 14:00 データ保存（9時半比含む）完了")
        return

    save_json(data, SAVE_PATH)
    print("⚠️ 通常時間の保存（テスト）完了")

if __name__ == "__main__":
    main()
