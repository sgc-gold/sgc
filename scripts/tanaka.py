import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, To, From, Subject, HtmlContent,
    Attachment, FileContent, FileName, FileType, Disposition, ContentId
)
from datetime import datetime
import requests
import math
import re
import json
import os

# ==================================================
# メール設定（SendGrid経由）
# ==================================================
SENDGRID_API_KEY = os.environ["SENDGRID_API_KEY"]
FROM_EMAIL       = "yokomori@sgc-gold.co.jp"
TO_EMAIL         = "yokomori@sgc-gold.co.jp"
BCC_EMAILS       = [
    "s.forest.1127@gmail.com",
]

DEFAULT_SPREAD = {
    "金":     325,
    "プラチナ": 385,
    "銀":      15.5
}

LINEWORKS_WEBHOOK_URL = os.environ["LINEWORKS_WEBHOOK_URL"]

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
CHART_FILES      = {
    "xaujpy": os.path.join(SCRIPT_DIR, "chart_xaujpy.png"),
    "xauusd": os.path.join(SCRIPT_DIR, "chart_xauusd.png"),
    "usdjpy": os.path.join(SCRIPT_DIR, "chart_usdjpy.png"),
}


# ==================================================
# data/tanaka_price.json から価格を読み込む
# （スクレイピングはupdate_tanaka.pyが担当）
# ==================================================
PRICE_FILE = os.path.join(SCRIPT_DIR, "..", "data", "tanaka_price.json")

METAL_KEY_MAP = {
    "GOLD":     ("金",     False),
    "PLATINUM": ("プラチナ", False),
    "SILVER":   ("銀",     True),   # True = 銀（小数点あり）
}

def get_commodity_prices():
    if not os.path.exists(PRICE_FILE):
        raise FileNotFoundError(f"価格ファイルが見つかりません: {PRICE_FILE}")

    with open(PRICE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    date_info = data["update_time"]
    raw = data["prices"]

    def to_float(v):
        return float(str(v).replace(",", "").replace("+", "").replace("円", "").strip())

    prices = {}
    for eng_key, (jpn_key, is_silver) in METAL_KEY_MAP.items():
        p = raw[eng_key]
        prices[jpn_key] = {
            "retail":        to_float(p["retail"]),
            "purchase":      to_float(p["buy"]),
            "retail_diff":   p["retail_diff"],
            "purchase_diff": p["buy_diff"],
        }

    return date_info, prices


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
        def fmt_diff(metal, val):
            v = str(val).strip()
            if not v or v == "0":
                return "変わらず"
            # すでに「円」が含まれていればそのまま
            if "円" in v:
                return v
            return v + " 円"
        return f"""
<tr style="color:#666; font-size:14px;">
  <th style="padding:2px 12px; text-align:center; border-bottom:1px solid #eee; white-space:nowrap;">{title}</th>
  <td style="padding:2px 12px; border-bottom:1px solid #eee; background:{colors['金']}; text-align:center; white-space:nowrap;">{fmt_diff('金',     prices['金'][f'{kind}_diff'])}</td>
  <td style="padding:2px 12px; border-bottom:1px solid #eee; background:{colors['プラチナ']}; text-align:center; white-space:nowrap;">{fmt_diff('プラチナ', prices['プラチナ'][f'{kind}_diff'])}</td>
  <td style="padding:2px 12px; border-bottom:1px solid #eee; background:{colors['銀']}; text-align:center; white-space:nowrap;">{fmt_diff('銀',     prices['銀'][f'{kind}_diff'])}</td>
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
            price         = prices[metal][kind]
            day_diff_text = prices[metal][f"{kind}_diff"]

            if metal == "銀":
                value    = float(re.sub(r"[^\d\.\-]", "", day_diff_text))
                day_diff = "変わらず" if abs(value) < 0.0001 else f"{value:+.2f}円"
            else:
                num      = re.sub(r"[^\d\-]", "", day_diff_text)
                value    = int(num) if num else 0
                day_diff = "変わらず" if value == 0 else day_diff_text.strip() + "円"

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
print(f"📅 価格ファイルの公表時刻: {date_info}")

# 17:00以降の更新はスキップ
m_time = re.search(r'(\d{1,2}):(\d{2})公表', date_info)
if m_time:
    update_hour = int(m_time.group(1))
    if update_hour >= 17:
        print(f"⏭ 17:00以降の更新のためスキップ（{date_info}）")
        exit(0)

spread        = calculate_spread(new_prices)
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

# 9時半比はdata/tanaka_price.jsonに既に計算済みの値を使用
nine_thirty_diff = {}
if "09:30" not in date_info:
    with open(PRICE_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    raw_prices = raw_data["prices"]

    def to_float_diff(v):
        try:
            return float(str(v).replace(",", "").replace("+", "").strip())
        except:
            return 0.0

    has_930diff = any(
        "retail_930diff" in raw_prices[k]
        for k in raw_prices
        if raw_prices[k].get("retail_930diff", "") != ""
    )
    if has_930diff:
        for eng_key, (jpn_key, _) in METAL_KEY_MAP.items():
            p = raw_prices[eng_key]
            nine_thirty_diff[jpn_key] = {
                "purchase": to_float_diff(p.get("buy_930diff", 0)),
                "retail":   to_float_diff(p.get("retail_930diff", 0)),
            }
        print("✅ 9時半比をtanaka_price.jsonから取得しました")
    else:
        print("⚠ 9時半比データなし（9時半の更新かデータ未取得）")

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
