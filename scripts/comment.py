import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ログ書き込み用関数
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(BASE_DIR, "comment_log.txt"), "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")

url = "https://nanboya.com/gold-kaitori/souba/"
response = requests.get(url)
response.encoding = response.apparent_encoding

soup = BeautifulSoup(response.text, "html.parser")

time_tag = soup.find("p", class_="expert-comment--time")

if time_tag:
    time_text = time_tag.get_text(strip=True)
    log(f"取得した time_text: {time_text}")

    match = re.search(r"\d{4}年\d{1,2}月\d{1,2}日", time_text)
    if match:
        comment_date = match.group()
        log(f"抽出された年月日: {comment_date}")

        # 文字列を日付オブジェクトに変換
        comment_date_obj = datetime.strptime(comment_date, "%Y年%m月%d日").date()
    else:
        log("年月日のパターンが抽出できませんでした。")
        comment_date_obj = None

    # 今日の日付（オブジェクト）
    today_date = datetime.now().date()
    # ログには統一してゼロ埋め付きで出す
    log(f"今日の日付: {today_date.strftime('%Y年%m月%d日')}")

    if comment_date_obj != today_date:
        log("本日の日付ではないため、処理をスキップしました。")
        print("本日の日付ではないため、処理をスキップします。")
    else:
        comment_tag = soup.find("p", class_="expert-comment--comment")
        if comment_tag:
            comment_text = comment_tag.get_text(strip=True)

            sentences = comment_text.split("。")
            formatted_text = "\n".join(s + "。" for s in sentences if s.strip())

            with open(os.path.join(BASE_DIR, "comment.txt"), "w", encoding="utf-8") as f:
                f.write(formatted_text)

            log("コメントを保存しました。")
            log(f"コメント本文:\n{formatted_text}")
            print("コメントを「。」で改行してcomment.txtに保存しました。")
        else:
            log("コメントが見つかりませんでした。")
            print("コメントが見つかりませんでした。")
else:
    log("日付タグが見つかりませんでした。")
    print("日付タグが見つかりませんでした。")
