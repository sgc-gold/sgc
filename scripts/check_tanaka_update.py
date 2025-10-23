import requests
from bs4 import BeautifulSoup
import hashlib
import os

URL = "https://gold.tanaka.co.jp/commodity/souba/english/index.php"
HASH_FILE = "tanaka_hash.txt"

def get_h3_hash():
    res = requests.get(URL, timeout=10)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")
    h3_span = soup.select_one("h3 span")
    if not h3_span:
        raise ValueError("h3 span が見つかりません")
    text = h3_span.text.strip()
    hash_value = hashlib.md5(text.encode("utf-8")).hexdigest()
    return hash_value, text

def load_previous_hash():
    if not os.path.exists(HASH_FILE):
        return None
    with open(HASH_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def save_hash(hash_value):
    with open(HASH_FILE, "w", encoding="utf-8") as f:
        f.write(hash_value)

def main():
    current_hash, update_text = get_h3_hash()
    prev_hash = load_previous_hash()

    print(f"📅 公表時刻: {update_text}")

    if current_hash == prev_hash:
        print("⏸ ハッシュに変化なし → 更新スキップ")
        exit(1)

    print("✅ ハッシュが変化 → データ更新開始")
    save_hash(current_hash)
    print("💾 ハッシュ更新完了")

if __name__ == "__main__":
    main()
