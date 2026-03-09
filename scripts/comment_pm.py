import requests
from bs4 import BeautifulSoup
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

keyword_priority = [
    ("今夜のシナリオ金", "comment_pm.txt", True),
    ("午後の金相場", "comment_pm.txt", False),
]

base_url = "https://fu.minkabu.jp/news?page="

def find_article_by_keywords():
    page = 1
    while True:
        url = base_url + str(page)
        print(f"🔍 ページ {page} チェック中: {url}")
        res = requests.get(url)
        if res.status_code != 200:
            print("⚠️ ページ取得に失敗しました。終了。")
            break

        soup = BeautifulSoup(res.text, "html.parser")
        articles = soup.find_all("li", class_="p-2 border-b border-slate-300")
        if not articles:
            print("❌ 記事が見つかりません。終了。")
            break

        for article in articles:
            a_tag = article.find("a", class_="text-blue-700")
            if not a_tag:
                continue
            title = a_tag.text.strip()
            href = a_tag.get("href")
            full_url = "https://fu.minkabu.jp" + href

            for kw, filename, remove_last in keyword_priority:
                if kw in title:
                    print(f"✅ キーワード「{kw}」ヒット: {title}")
                    return title, full_url, filename, remove_last

        page += 1

        if page > 10:
            print("⚠️ 最大ページ数に達しました。終了。")
            break

    return None

def get_article_content(url, remove_last_line=False):
    res = requests.get(url)
    if res.status_code != 200:
        return "⚠️ 記事本文の取得に失敗しました。"

    soup = BeautifulSoup(res.text, "html.parser")
    content_tag = soup.find("pre", class_="ui-article")

    if not content_tag:
        return "⚠️ 本文が見つかりませんでした。"

    text = content_tag.get_text(strip=True)
    lines = text.splitlines()
    filtered_lines = [line for line in lines if "MINKABU PRESS" not in line]
    filtered_text = "".join(filtered_lines)

    split_text = filtered_text.split("。")
    split_text = [s.strip() for s in split_text if s.strip()]
    joined_text = "。\n".join(split_text) + "。"

    final_lines = joined_text.strip().splitlines()

    if remove_last_line and len(final_lines) > 1:
        final_lines = final_lines[:-1]

    return "\n".join(final_lines)

def main():
    result = find_article_by_keywords()
    filename = "comment_pm.txt"  # ファイル名は固定

    if not result:
        message = "❌ 該当記事は見つかりませんでした。"
        print(message)
        with open(os.path.join(BASE_DIR, filename), "w", encoding="utf-8") as f:
            f.write(message + "\n")
        return

    title, url, filename, remove_last = result
    content = get_article_content(url, remove_last)

    print(f"💾 「{title}」を {filename} に保存中（最後の行削除: {remove_last}）")
    with open(os.path.join(BASE_DIR, filename), "w", encoding="utf-8") as f:
        f.write(content + "\n")

if __name__ == "__main__":
    main()
