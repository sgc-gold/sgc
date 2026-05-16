import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation


HISTORY_DIR = os.path.join("data", "history")
INDEX_PATH = os.path.join(HISTORY_DIR, "index.json")


def parse_date(value):
    return datetime.strptime(value.strip(), "%Y/%m/%d")


def parse_time(value):
    raw = value.strip()
    hour, minute = raw.split(":")
    return f"{int(hour):02d}:{int(minute):02d}"


def decimal_value(value):
    raw = str(value).strip().replace(",", "")
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid number: {value}") from exc


def format_integer(value, signed=False):
    number = decimal_value(value)
    if number is None:
        return ""
    integer = int(number)
    if signed and integer > 0:
        return f"+{integer:,}"
    return f"{integer:,}"


def format_decimal(value, signed=False):
    number = decimal_value(value)
    if number is None:
        return ""
    text = f"{number.quantize(Decimal('0.01')):,.2f}"
    if signed and number > 0:
        return "+" + text
    return text


def snapshot_from_row(row):
    date = parse_date(row["公表日"])
    time_text = parse_time(row["公表時刻"])
    update_time = f"{date:%Y年%m月%d日} {time_text}公表（日本時間）"

    return {
        "update_time": update_time,
        "prices": {
            "GOLD": {
                "retail": format_integer(row["金売"]),
                "retail_diff": format_integer(row["金売前日比"], signed=True),
                "buy": format_integer(row["金買"]),
                "buy_diff": format_integer(row["金買前日比"], signed=True),
            },
            "PLATINUM": {
                "retail": format_integer(row["Pt売"]),
                "retail_diff": format_integer(row["Pt売前日比"], signed=True),
                "buy": format_integer(row["Pt買"]),
                "buy_diff": format_integer(row["Pt買前日比"], signed=True),
            },
            "SILVER": {
                "retail": format_decimal(row["銀売"]),
                "retail_diff": format_decimal(row["銀売前日比"], signed=True),
                "buy": format_decimal(row["銀買"]),
                "buy_diff": format_decimal(row["銀買前日比"], signed=True),
            },
        },
    }


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_tanaka_history.py <history.csv>", file=sys.stderr)
        return 2

    csv_path = sys.argv[1]
    grouped = defaultdict(list)

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = parse_date(row["公表日"])
            grouped[f"{date:%Y-%m-%d}"].append(row)

    files = []
    for date_key in sorted(grouped):
        rows = sorted(grouped[date_key], key=lambda r: parse_time(r["公表時刻"]))
        snapshots = [snapshot_from_row(row) for row in rows]
        path = os.path.join(HISTORY_DIR, f"{date_key}.json")
        write_json(path, {"date": date_key, "snapshots": snapshots})
        files.append(f"{date_key}.json")

    write_json(INDEX_PATH, {"files": files})
    print(f"Imported {sum(len(rows) for rows in grouped.values())} snapshots into {len(files)} history files.")


if __name__ == "__main__":
    raise SystemExit(main())
