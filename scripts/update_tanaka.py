import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

url = "https://gold.tanaka.co.jp/commodity/souba/english/index.php"
res = requests.get(url)
res.encoding = 'iso-8859-1'
soup = BeautifulSoup(res.text, 'html.parser')

prices = {}
prices["GOLD"] = soup.select_one("tr.gold td.purchase_tax").text.strip()
prices["PLATINUM"] = soup.select_one("tr.pt td.purchase_tax").text.strip()
prices["SILVER"] = soup.select_one("tr.silver td.purchase_tax").text.strip()

data = {
    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "prices": prices
}

with open("data/tanaka_price.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
