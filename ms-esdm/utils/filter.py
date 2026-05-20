import re
import calendar
from datetime import datetime, timedelta
from dateparser.search import search_dates

MONTHS_ID = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12
}

# Terms that indicate a date or time span
DATE_KEYWORDS = [
    "tanggal", "tgl", "sampai", "sd", "hingga",
    "mulai", "dari", "hari ini", "kemarin", "bulan", "minggu", "tahun",
    "januari","februari","maret","april","mei","juni","juli","agustus",
    "september","oktober","november","desember"
]

def extract_date_range(text: str):
    text_lower = text.lower()

    # Strict: return None if no date/time keyword
    if not any(k in text_lower for k in DATE_KEYWORDS):
        return None

    today = datetime.now()
    yesterday = today - timedelta(days=1)

    # 1️⃣ Detect "month year" in Indonesian
    month_regex = r"(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s+(20\d{2})"
    match = re.search(month_regex, text_lower)
    if match:
        month_name = match.group(1)
        year = int(match.group(2))
        month = MONTHS_ID[month_name]

        start = datetime(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = datetime(year, month, last_day)

        # Clamp end to yesterday
        if end > yesterday:
            end = yesterday

        # Ignore future months
        if start > yesterday:
            return None

        if end < start:
            end = start

        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    # 2️⃣ Fallback: search_dates
    parsed = search_dates(
        text_lower,
        languages=["id", "en"],
        settings={
            "PREFER_DATES_FROM": "past",
            "PREFER_DAY_OF_MONTH": "first"
        }
    )

    if parsed:
        dates = [d[1] for d in parsed]
        start = min(dates)
        end = max(dates)

        # Clamp to yesterday
        if end > yesterday:
            end = yesterday
        if start > yesterday:
            return None
        if end < start:
            end = start

        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    # No valid date found
    return None