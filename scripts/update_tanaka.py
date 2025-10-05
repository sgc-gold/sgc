import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

url = "https://gold.tanaka.co.jp/commodity/souba/english/index.php"
res = requests.get(url)
res.encoding = 'iso-8859-1'
soup = BeautifulSoup(res.text, 'html.parser')

def get_text(selector):
    el = soup.select_one(selector)
    return el.text.strip() if el else "N/A"

data = {
    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "prices": {
        "GOLD": {
            "buy": get_text("tr.gold td.purchase_tax"),
            "sell": get_text("tr.gold td.retail_tax")
        },
        "PLATINUM": {
            "buy": get_text("tr.pt td.purchase_tax"),
            "sell": get_text("tr.pt td.retail_tax")
        },
        "SILVER": {
            "buy": get_text("tr.silver td.purchase_tax"),
            "sell": get_text("tr.silver td.retail_tax")
        }
    }
}

with open("data/tanaka_price.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
