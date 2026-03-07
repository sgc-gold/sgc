import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, To, From, Subject, HtmlContent,
    Attachment, FileContent, FileName, FileType, Disposition, ContentId
)
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import math
import re
import json
import os

# ==================================================
# メール設定（SendGrid経由）
# ==================================================
SENDGRID_API_KEY = os.environ["SENDGRID_API_KEY"]  # GitHub Secret: SENDGRID_API_KEY
FROM_EMAIL       = "yokomori@sgc-gold.co.jp"
TO_EMAIL         = "yokomori@sgc-gold.co.jp"
BCC_EMAILS       = [
    "s.forest.1127@gmail.com",
    "junjunjunjun@docomo.ne.jp",
    "hayakichibou@docomo.ne.jp",
    "ishikawa@sgc-gold.co.jp",
    "tomori@sgc-gold.co.jp",
    "k-tsuchiya@sgc-gold.co.jp",
    "tsuchiya@sgc-gold.co.jp",
    "y-hosaka@sgc-gold.co.jp"
]

DEFAULT_SPREAD = {
    "金":     325,
    "プラチナ": 385,
    "銀":      15.5
}

# LINE WORKSのWebhook URLもSecretsから取得
LINEWORKS_WEBHOOK_URL = os.environ["LINEWORKS_WEBHOOK_URL"]  # GitHub Secret: LINEWORKS_WEBHOOK_URL

# スクリプトと同じディレクトリ（scripts/）にファイルを置く
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
NINE_THIRTY_FILE = os.path.join(SCRIPT_DIR, "930_prices.json")
CHART_FILES   = {
    "xaujpy": os.path.join(SCRIPT_DIR, "chart_xaujpy.png"),
    "xauusd": os.path.join(SCRIPT_DIR, "chart_xauusd.png"),
    "usdjpy": os.path.join(SCRIPT_DIR, "chart_usdjpy.png"),
}


def get_commodity_prices():
    url = "https://gold.tanaka.co.jp/commodity/souba/english/index.php"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    date_info = soup.find("h3").find("span").text.strip()
    match = re.search(
        r"As of at (\d{1,2}:\d{2}) on ([A-Za-z]+) (\d{1,2})(st|nd|rd|th), (\d{4})",
        date_info
    )
    if match:
        time_str  = match.group(1)
        month_str = match.group(2)
        day       = int(match.group(3))
        year      = match.group(5)
        months = {
            "January": "1月", "February": "2月", "March": "3月",
            "April": "4月", "May": "5月", "June": "6月",
            "July": "7月", "August": "8月", "September": "9月",
            "October": "10月", "November": "11月", "December": "12月"
        }
        month_jp     = months.get(month_str, month_str)
        date_info_jp = f"{year}年{month_jp}{day}日 {time_str}公表（日本時間）"
    else:
        date_info_jp = date_info

    def parse_price_list(tag, index):
        return (
            soup.find_all("td", {"class": tag})[index]
            .text.strip().split(" ")[0]
            .replace("yen", "").replace(",", "")
        )

    prices = {
        "金": {
            "retail":        float(parse_price_list("retail_tax",    0)),
            "purchase":      float(parse_price_list("purchase_tax",  0)),
            "retail_diff":   soup.find("td", {"class": "retail_ratio"}).text.strip().replace("yen", "円"),
            "purchase_diff": soup.find("td", {"class": "purchase_ratio"}).text.strip().replace("yen", "円"),
        },
        "プラチナ": {
            "retail":        float(parse_price_list("retail_tax",    1)),
            "purchase":      float(parse_price_list("purchase_tax",  1)),
            "retail_diff":   soup.find_all("td", {"class": "retail_ratio"})[1].text.strip().replace("yen", "円"),
            "purchase_diff": soup.find_all("td", {"class": "purchase_ratio"})[1].text.strip().replace("yen", "円"),
        },
        "銀": {
            "retail":        float(parse_price_list("retail_tax",    2)),
            "purchase":      float(parse_price_list("purchase_tax",  2)),
            "retail_diff":   soup.find_all("td", {"class": "retail_ratio"})[2].text.strip().replace("yen", "円"),
            "purchase_diff": soup.find_all("td", {"class": "purchase_ratio"})[2].text.strip().replace("yen", "円"),
        },
    }
    return date_info_jp, prices


def calculate_spread(prices):
    spread = {}
    for metal in prices:
        retail   = prices[metal]["retail"]
        purchase = prices[metal]["purchase"]
        if metal == "銀":
            spread[metal] = round((retail - purchase) / 1.1, 2)
        else:
            retail_divided   = round(retail   / 1.1, 10)
            retail_spread    = int(retail_divided)   if retail_divided.is_integer()   else math.ceil(retail_divided)
            purchase_divided = round(purchase / 1.1, 10)
            purchase_spread  = int(purchase_divided) if purchase_divided.is_integer() else math.floor(purchase_divided)
            spread[metal]    = retail_spread - purchase_spread
    return spread


def check_spread_change(spread):
    report = ""
    for metal in spread:
        default = DEFAULT_SPREAD[metal]
        if spread[metal] == default:
            report += f"{metal}　{default}円\n"
        else:
            report += f"{metal}　{default}円　⇒　{spread[metal]}円\n"
    return report


def format_diff(metal, diff):
    if abs(diff) < 0.01:
        return "変わらず"
    return f"{diff:+.2f} 円" if metal == "銀" else f"{int(round(diff)):+,} 円"


def generate_price_table(prices, nine_thirty_diff=None):
    show_diff_930 = nine_thirty_diff is not None
    colors = {
        "金":     "#FFF8DC",
        "プラチナ": "#E0E5E8",
        "銀":     "#DCE9F9",
    }

    def row_price(title, kind):
        return f"""
<tr style="background:#f5f5f5; font-weight:bold; color:#444;">
  <th style="padding:8px 12px; text-align:center; border-bottom:1px solid #ccc; white-space:nowrap;">{title}</th>
  <td style="padding:8px 12px; border-bottom:1px solid #ccc; background:{colors['金']}; white-space:nowrap;">{int(prices['金'][kind]):,}円</td>
  <td style="padding:8px 12px; border-bottom:1px solid #ccc; background:{colors['プラチナ']}; white-space:nowrap;">{int(prices['プラチナ'][kind]):,}円</td>
  <td style="padding:8px 12px; border-bottom:1px solid #ccc; background:{colors['銀']}; white-space:nowrap;">{prices['銀'][kind]:.2f}円</td>
</tr>
"""

    def row_diff(title, kind):
        return f"""
<tr style="color:#666; font-size:14px;">
  <th style="padding:2px 12px; text-align:center; border-bottom:1px solid #eee; white-space:nowrap;">{title}</th>
  <td style="padding:2px 12px; border-bottom:1px solid #eee; background:{colors['金']}; text-align:center; white-space:nowrap;">{prices['金'][f'{kind}_diff']}</td>
  <td style="padding:2px 12px; border-bottom:1px solid #eee; background:{colors['プラチナ']}; text-align:center; white-space:nowrap;">{prices['プラチナ'][f'{kind}_diff']}</td>
  <td style="padding:2px 12px; border-bottom:1px solid #eee; background:{colors['銀']}; text-align:center; white-space:nowrap;">{prices['銀'][f'{kind}_diff']}</td>
</tr>
"""

    def row_diff_930(kind):
        return f"""
<tr style="color:#666; font-size:14px;">
  <th style="padding:2px 12px; text-align:center; border-bottom:1px solid #eee; white-space:nowrap;">9時半比</th>
  <td style="padding:2px 12px; border-bottom:1px solid #eee; background:{colors['金']}; text-align:center; white-space:nowrap;">{format_diff('金',     nine_thirty_diff.get('金',     {}).get(kind, 0))}</td>
  <td style="padding:2px 12px; border-bottom:1px solid #eee; background:{colors['プラチナ']}; text-align:center; white-space:nowrap;">{format_diff('プラチナ', nine_thirty_diff.get('プラチナ', {}).get(kind, 0))}</td>
  <td style="padding:2px 12px; border-bottom:1px solid #eee; background:{colors['銀']}; text-align:center; white-space:nowrap;">{format_diff('銀',     nine_thirty_diff.get('銀',     {}).get(kind, 0))}</td>
</tr>
"""

    html = f"""
<table border="0" cellpadding="0" cellspacing="0" style="
    border-collapse:collapse; font-family:'Segoe UI',sans-serif; font-size:14px; text-align:center;
    width:100%; max-width:600px; margin:10px 0; box-shadow:0 4px 12px rgba(0,0,0,0.12); border-radius:8px; overflow:hidden;">
  <thead style="background:#003366; color:#fff; font-weight:bold; font-size:15px;">
    <tr>
      <th style="padding:14px 16px; text-align:center; white-space:nowrap;">&nbsp;</th>
      <th style="padding:14px 16px; border-right:1px solid #002244; white-space:nowrap;">金</th>
      <th style="padding:14px 16px; border-right:1px solid #002244; white-space:nowrap;">プラチナ</th>
      <th style="padding:14px 16px; white-space:nowrap;">銀</th>
    </tr>
  </thead>
  <tbody>
    {row_price("買取価格", "purchase")}
    {row_diff("前日比",   "purchase")}
    {row_diff_930("purchase") if show_diff_930 else ""}
    {row_price("小売価格", "retail")}
    {row_diff("前日比",   "retail")}
    {row_diff_930("retail") if show_diff_930 else ""}
  </tbody>
</table>
"""
    return html


def add_weekday_to_dateinfo(date_info):
    try:
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_info)
        if not m:
            return date_info
        year, month, day = map(int, m.groups())
        dt      = datetime(year, month, day)
        weekday = "月火水木金土日"[dt.weekday()]
        return date_info.replace(
            f"{year}年{month}月{day}日",
            f"{year}年{month}月{day}日（{weekday}）"
        )
    except Exception:
        return date_info


def format_line_diff(value, metal=None):
    if abs(value) < 0.0001:
        return "変わらず"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}円" if metal == "銀" else f"{sign}{int(round(value))}円"


def build_lineworks_message(date_info, prices, nine_thirty_diff, spread, comment_text):
    is_930         = "09:30" in date_info
    spread_changed = any(spread[m] != DEFAULT_SPREAD[m] for m in spread)
    lines          = []

    if spread_changed:
        lines += ["※スプレッド変更あり", ""]

    date_with_weekday = add_weekday_to_dateinfo(
        date_info.replace("公表（日本時間）", " 更新")
    )
    lines += [date_with_weekday, ""]

    if not is_930 and nine_thirty_diff is not None:
        lines += ["※（前日比／9時半比）", ""]

    for metal in ["金", "プラチナ", "銀"]:
        lines.append(f"■ {metal}")
        kinds = [("purchase", "買取"), ("retail", "小売")] if metal == "金" else [("purchase", "買取")]

        for kind, label in kinds:
            price        = prices[metal][kind]
            day_diff_text = prices[metal][f"{kind}_diff"]

            if metal == "銀":
                value    = float(re.sub(r"[^\d\.\-]", "", day_diff_text))
                day_diff = "変わらず" if abs(value) < 0.0001 else f"{value:+.2f}円"
            else:
                num      = re.sub(r"[^\d\-]", "", day_diff_text)
                value    = int(num) if num else 0
                day_diff = "変わらず" if value == 0 else day_diff_text.replace("yen", "").strip()

            price_str = f"{price:.2f}円" if metal == "銀" else f"{int(price):,}円"
            line      = f"{label}：{price_str}（{day_diff}"

            if not is_930 and nine_thirty_diff is not None:
                diff_930 = format_line_diff(
                    nine_thirty_diff.get(metal, {}).get(kind, 0), metal
                )
                line += f"／{diff_930}"

            line += "）"
            lines.append(line)

        lines.append("")

    spread_lines = [
        f"{metal}：{DEFAULT_SPREAD[metal]}円 → {spread[metal]}円"
        for metal in spread if spread[metal] != DEFAULT_SPREAD[metal]
    ]
    if spread_lines:
        lines += ["■ スプレッド（税抜）"] + spread_lines + [""]

    if comment_text:
        lines += ["■ 市況コメント", comment_text]

    return "\n".join(lines)


# ==================================================
# メイン処理
# ==================================================
date_info, new_prices = get_commodity_prices()
spread       = calculate_spread(new_prices)
spread_report = check_spread_change(spread)

subject = "【田中貴金属】 価格更新通知　(株)SGC横森"
if any(spread[metal] != DEFAULT_SPREAD[metal] for metal in spread):
    subject = "【田中貴金属】 価格更新通知 ※スプレッド変更　(株)SGC横森"
spread_notice = "【要確認】 スプレッドに変更がありました" if "※" in subject else ""

# コメントファイル読み込み
comment_text = ""
if "09:30" in date_info:
    comment_file = os.path.join(SCRIPT_DIR, "comment.txt")
elif "14:00" in date_info:
    comment_file = os.path.join(SCRIPT_DIR, "comment_pm.txt")
else:
    comment_file = ""

if comment_file and os.path.exists(comment_file):
    with open(comment_file, "r", encoding="utf-8") as f:
        comment_text = f.read().strip()

# 9:30価格の保存・読み込み
if "09:30" in date_info:
    with open(NINE_THIRTY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_prices, f, ensure_ascii=False, indent=2)

nine_thirty_diff = {}
if "09:30" not in date_info and os.path.exists(NINE_THIRTY_FILE):
    with open(NINE_THIRTY_FILE, "r", encoding="utf-8") as f:
        prices_930 = json.load(f)
    for metal in ["金", "プラチナ", "銀"]:
        nine_thirty_diff[metal] = {
            "purchase": new_prices[metal]["purchase"] - prices_930[metal]["purchase"],
            "retail":   new_prices[metal]["retail"]   - prices_930[metal]["retail"],
        }

# メール本文 HTML 組み立て
ny_comment_html = ""
if comment_text:
    ny_comment_html = f"<p><strong>📌 市況コメント</strong><br>{comment_text.replace(chr(10), '<br>')}</p>"

chart_titles = {
    "xaujpy": "■金 円建て価格チャート",
    "xauusd": "■金 ドル建て価格チャート",
    "usdjpy": "■ドル円 為替チャート",
}
chart_html = ""
for key, path in CHART_FILES.items():
    if os.path.exists(path):
        chart_html += f'<p><strong>{chart_titles[key]}</strong><br><img src="cid:{key}" width="700"></p>\n'
    else:
        chart_html += f"<p>⚠ チャート画像（{os.path.basename(path)}）が見つかりませんでした。</p>\n"

price_table_html = generate_price_table(new_prices, nine_thirty_diff if nine_thirty_diff else None)

body = f"""
<p style="background-color:#fff8e1; color:#bfa100; font-weight:bold; padding:8px 12px; border-radius:4px; border:1px solid #f0e68c;">
  ▶ 田中貴金属 価格情報
</p>
<p>{date_info}<br>{spread_notice}</p>
{price_table_html}
<p>■スプレッド（税抜）<br>{spread_report.replace(chr(10), '<br>')}</p>
<p style="background-color:#eef7ff; color:#004080; font-weight:bold; padding:8px 12px; border-radius:4px; border:1px solid #cce0ff;">
  ▶ 市況情報
</p>
{chart_html}
{ny_comment_html}
<p style="font-size:11px; color:#888; margin-top:30px;">
本メールはプログラムによる自動送信です。最新の価格は公式サイトをご確認ください。<br>
<a href="https://gold.tanaka.co.jp/commodity/souba/index.php">▶ 田中貴金属価格情報</a>
</p>
"""

msg = Mail(
    from_email=From(FROM_EMAIL, "（株）SGC 横森俊一"),
    to_emails=[To(TO_EMAIL)] + [To(bcc) for bcc in BCC_EMAILS],
    subject=Subject(subject),
    html_content=HtmlContent(body)
)

# チャート画像を添付（インライン埋め込み）
for key, path in CHART_FILES.items():
    if os.path.exists(path):
        with open(path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode()
        attachment = Attachment(
            FileContent(encoded),
            FileName(os.path.basename(path)),
            FileType("image/png"),
            Disposition("inline"),
            ContentId(key)
        )
        msg.attachment = attachment

sg = SendGridAPIClient(SENDGRID_API_KEY)
response = sg.send(msg)
print(f"✅ メール送信完了 (status: {response.status_code})")

# LINE WORKS 送信
lineworks_message = build_lineworks_message(
    date_info, new_prices,
    nine_thirty_diff if nine_thirty_diff else None,
    spread, comment_text
)

response = requests.post(
    LINEWORKS_WEBHOOK_URL,
    headers={"Content-Type": "application/json"},
    json={"body": {"text": lineworks_message}}
)
print("LINE WORKS response:", response.status_code)
if response.status_code != 200:
    print(response.text)
