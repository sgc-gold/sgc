import os
import random
import re
import time
import zoneinfo
from datetime import datetime

import requests
from bs4 import BeautifulSoup


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MAX_RETRY = 3
RETRY_BASE_WAITS = [0, 20, 75]
RETRY_JITTER_MAX = 20
TIMEOUT = 30
NANBOYA_URL = "https://nanboya.com/gold-kaitori/souba/"
DATE_PATTERN = r"\d{4}\u5e74\d{1,2}\u6708\d{1,2}\u65e5"
DATE_FORMAT = "%Y\u5e74%m\u6708%d\u65e5"
FULL_STOP = "\u3002"


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(BASE_DIR, "comment_log.txt"), "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")


def warn(message):
    text = f"WARNING: {message}"
    log(text)
    print(text)


def create_session():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://nanboya.com/",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    return session


def response_log_info(response):
    return {
        "url": response.url,
        "status_code": response.status_code,
        "date": response.headers.get("Date", ""),
        "x_cache": response.headers.get("X-Cache", ""),
        "age": response.headers.get("Age", ""),
        "server": response.headers.get("Server", ""),
        "content_type": response.headers.get("Content-Type", ""),
    }


def fetch_comment(session, attempt):
    params = {"cb": str(int(time.time()))}
    try:
        response = session.get(NANBOYA_URL, params=params, timeout=TIMEOUT)
    except requests.Timeout as exc:
        warn(f"[attempt {attempt}] Nanboya fetch timed out: {exc}")
        return None
    except requests.RequestException as exc:
        warn(f"[attempt {attempt}] Nanboya fetch request failed: {exc}")
        return None

    info = response_log_info(response)
    log(f"[attempt {attempt}] fetch_comment: {info}")

    if response.status_code != 200:
        warn(f"[attempt {attempt}] Nanboya returned HTTP {response.status_code}: {info}")
        return None

    response.encoding = "utf-8"
    try:
        return BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        warn(f"[attempt {attempt}] Nanboya HTML parse failed: {exc}")
        return None


def wait_before_attempt(attempt):
    base_wait = RETRY_BASE_WAITS[attempt - 1] if attempt <= len(RETRY_BASE_WAITS) else RETRY_BASE_WAITS[-1]
    if base_wait <= 0:
        log(f"[attempt {attempt}] starting immediately.")
        print(f"[attempt {attempt}] Starting Nanboya comment fetch immediately.")
        return

    wait_seconds = base_wait + random.randint(0, RETRY_JITTER_MAX)
    log(f"[attempt {attempt}] waiting {wait_seconds}s before retry.")
    print(f"[attempt {attempt}] Waiting {wait_seconds}s before retrying Nanboya comment fetch...")
    time.sleep(wait_seconds)


def extract_comment_text(soup):
    comment_tag = soup.find("p", class_="expert-comment--comment")
    if not comment_tag:
        return None
    comment_text = comment_tag.get_text(strip=True)
    sentences = comment_text.split(FULL_STOP)
    return "\n".join(s + FULL_STOP for s in sentences if s.strip())


def save_comment(text):
    with open(os.path.join(BASE_DIR, "comment.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def main():
    today_date = datetime.now(zoneinfo.ZoneInfo("Asia/Tokyo")).date()
    log(f"today: {today_date.isoformat()}")

    session = create_session()
    formatted_text = None

    for attempt in range(1, MAX_RETRY + 1):
        wait_before_attempt(attempt)
        soup = fetch_comment(session, attempt)
        if soup is None:
            pass
        else:
            time_tag = soup.find("p", class_="expert-comment--time")

            if not time_tag:
                warn(f"[attempt {attempt}] Nanboya comment time tag was not found.")
            else:
                time_text = time_tag.get_text(strip=True)
                log(f"[attempt {attempt}] time_text: {time_text}")

                match = re.search(DATE_PATTERN, time_text)
                if not match:
                    warn(f"[attempt {attempt}] Nanboya comment date pattern was not found: {time_text}")
                else:
                    comment_date = match.group()
                    try:
                        comment_date_obj = datetime.strptime(comment_date, DATE_FORMAT).date()
                    except ValueError as exc:
                        warn(f"[attempt {attempt}] Nanboya comment date parse failed: {comment_date} ({exc})")
                    else:
                        log(f"[attempt {attempt}] parsed comment_date: {comment_date}")

                        if comment_date_obj == today_date:
                            formatted_text = extract_comment_text(soup)
                            if formatted_text:
                                break
                            warn(f"[attempt {attempt}] Nanboya comment body tag was not found or was empty.")
                        else:
                            warn(
                                f"[attempt {attempt}] Nanboya comment is not for today: "
                                f"{comment_date_obj.isoformat()} != {today_date.isoformat()}"
                            )

    if formatted_text:
        save_comment(formatted_text)
        log("comment saved.")
        log(f"comment body:\n{formatted_text}")
        print("Saved Nanboya comment to comment.txt.")
    else:
        save_comment("")
        warn("Nanboya comment could not be fetched. Wrote empty comment.txt and continuing.")


if __name__ == "__main__":
    main()
