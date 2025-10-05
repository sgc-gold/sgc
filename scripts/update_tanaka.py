import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

url = "https://gold.tanaka.co.jp/commodity/souba/english/index.php"
res = requests.get(url)
res.encoding = 'iso-8859-1'
soup = BeautifulSoup(res.text, 'html.parser')

prices = {}

for metal, cls in [("GOLD", "gold"), ("PLATINUM", "pt"), ("SILVER", "silver")]:
    # 買取価格と前日比
    buy = soup.select_one(f"tr.{cls} td.purchase_tax").text.strip().replace(" yen","")
    buy_diff = soup.select_one(f"tr.{cls} td.purchase_ratio").text.strip().replace(" yen","")
    
    # 小売価格と前日比
    retail = soup.select_one(f"tr.{cls} td.retail_tax").text.strip().replace(" yen","")
    retail_diff = soup.select_one(f"tr.{cls} td.retail_ratio").text.strip().replace(" yen","")
    
    prices[metal] = {
        "buy": buy,
        "buy_diff": buy_diff,
        "retail": retail,
        "retail_diff": retail_diff
    }

data = {
    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "prices": prices
}

with open("data/tanaka_price.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
