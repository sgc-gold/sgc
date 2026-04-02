import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os
import time
import zoneinfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MAX_RETRY = 3
RETRY_WAIT = 300  # 5分

# ログ書き込み用関数
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(BASE_DIR, "comment_log.txt"), "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")

def fetch_comment():
    url = "https://nanboya.com/gold-kaitori/souba/"
    response = requests.get(url)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    return soup

def extract_comment_text(soup):
    comment_tag = soup.find("p", class_="expert-comment--comment")
    if not comment_tag:
        return None
    comment_text = comment_tag.get_text(strip=True)
    sentences = comment_text.split("。")
    return "\n".join(s + "。" for s in sentences if s.strip())

def save_comment(text):
    with open(os.path.join(BASE_DIR, "comment.txt"), "w", encoding="utf-8") as f:
        f.write(text)

today_date = datetime.now(zoneinfo.ZoneInfo("Asia/Tokyo")).date()
log(f"今日の日付: {today_date.strftime('%Y年%m月%d日')}")

soup = None
comment_date_obj = None
formatted_text = None

for attempt in range(1, MAX_RETRY + 1):
    soup = fetch_comment()
    time_tag = soup.find("p", class_="expert-comment--time")

    if not time_tag:
        log(f"[試行{attempt}] 日付タグが見つかりませんでした。")
        print(f"[試行{attempt}] 日付タグが見つかりませんでした。")
    else:
        time_text = time_tag.get_text(strip=True)
        log(f"[試行{attempt}] 取得した time_text: {time_text}")

        match = re.search(r"\d{4}年\d{1,2}月\d{1,2}日", time_text)
        if match:
            comment_date = match.group()
            comment_date_obj = datetime.strptime(comment_date, "%Y年%m月%d日").date()
            log(f"[試行{attempt}] 抽出された年月日: {comment_date}")

            if comment_date_obj == today_date:
                formatted_text = extract_comment_text(soup)
                break  # 今日のコメント取得成功
            else:
                log(f"[試行{attempt}] 本日の日付ではありません（{comment_date}）。")
                print(f"[試行{attempt}] nanboyaがまだ更新されていません（{comment_date}）。")
        else:
            # 日付パターンが取れない場合はリトライ（Noneのまま比較しない）
            log(f"[試行{attempt}] 年月日のパターンが抽出できませんでした。time_text={time_tag.get_text(strip=True) if time_tag else 'None'}")
            print(f"[試行{attempt}] 日付パターンが取得できませんでした。")

    if attempt < MAX_RETRY:
        print(f"{RETRY_WAIT // 60}分後にリトライします...")
        time.sleep(RETRY_WAIT)

# 結果の保存
if formatted_text:
    save_comment(formatted_text)
    log("コメントを保存しました。")
    log(f"コメント本文:\n{formatted_text}")
    print("コメントを「。」で改行してcomment.txtに保存しました。")
else:
    # 今日のコメントは取れなかった → 空にする
    save_comment("")
    log("本日のコメントを取得できなかったため、comment.txtを空にしました。")
    print("本日のコメントを取得できませんでした。comment.txtを空にします。")
