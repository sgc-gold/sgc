import requests
from bs4 import BeautifulSoup
import hashlib
import os
import subprocess
from datetime import datetime

# --- 設定 ---
URL = "https://gold.tanaka.co.jp/commodity/souba/english/index.php"
HASH_PATH = "tanaka_hash.txt"
UPDATE_SCRIPT = "scripts/update_tanaka.py"

def load_last_hash():
    if os.path.exists(HASH_PATH):
        with open(HASH_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def save_hash(h):
    with open(HASH_PATH, "w", encoding="utf-8") as f:
        f.write(h)

def fetch_current_hash():
    try:
        res = requests.get(URL, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        h3 = soup.select_one("h3 span")
        if h3 is None:
            print("⚠ <h3> spanタグが見つかりません")
            return None
        text = h3.text.strip()
        return hashlib.md5(text.encode("utf-8")).hexdigest(), text
    except Exception as e:
        print(f"⚠ ハッシュ取得エラー: {e}")
        return None, None

def main():
    last_hash = load_last_hash()
    current_hash, current_text = fetch_current_hash()
    if current_hash is None:
        print("⚠ 現在のハッシュが取得できず終了")
        return

    print(f"📅 現在の公表時刻: {current_text}")
    if last_hash == current_hash:
        print("⏸ ハッシュに変化なし → 更新スキップ")
        return

    print("✅ ハッシュが変化 → データ更新開始")
    try:
        subprocess.run(["python", UPDATE_SCRIPT], check=True)
        save_hash(current_hash)
        print("💾 ハッシュ更新完了")
    except Exception as e:
        print(f"⚠ 更新スクリプト実行エラー: {e}")

if __name__ == "__main__":
    main()
