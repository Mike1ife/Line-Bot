"""Stock quotes via the Yahoo Finance chart API.

One endpoint serves both markets; only the symbol suffix differs. Taiwan-listed
is `2330.TW`, Taiwanese OTC is `6488.TWO`, the TAIEX is `^TWII`, and US symbols
are bare. Responses come back in well under a second.

The official TWSE API is deliberately not called at request time - it can take
tens of seconds. Its data is baked into data/tw_stocks.json offline instead, by
tools/build_stock_names.py.
"""

import io
import json
import os
import requests
from datetime import datetime, timezone, timedelta

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
TIMEOUT = 10
TW = timezone(timedelta(hours=8))
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

TAIEX = "^TWII"
TPEX_INDEX = "^TWOII"
# A quote older than this is a closing price rather than a live one. Derived
# from the quote timestamp so there is no market-hours or holiday table to
# maintain, and no DST maths for the US session.
FRESH_WINDOW = timedelta(minutes=20)
# Taiwan's daily price limit is 10%; flag anything that pins against it.
LIMIT_THRESHOLD = 9.9

_NAMES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "tw_stocks.json",
)
_twStocks = None
_nameToCode = None


def _load_names():
    global _twStocks, _nameToCode
    if _twStocks is None:
        try:
            with io.open(_NAMES_PATH, encoding="utf-8") as f:
                _twStocks = json.load(f)
        except (OSError, ValueError):
            _twStocks = {}
        _nameToCode = {v["name"]: k for k, v in _twStocks.items()}
    return _twStocks, _nameToCode


def resolve_tw(query: str):
    """Code (2330) or Chinese name (台積電) -> (symbol, name, candidates).

    When a partial name matches several companies, return the candidates so the
    caller can ask rather than silently picking one.
    """
    stocks, nameToCode = _load_names()
    query = query.strip()

    code = query if query in stocks else nameToCode.get(query)
    if not code and query:
        matches = [(c, name) for name, c in nameToCode.items() if query in name]
        if len(matches) == 1:
            code = matches[0][0]
        elif matches:
            return None, None, sorted(matches)[:8]

    if not code:
        # Unknown to the local map; let Yahoo try it as a listed symbol.
        return (f"{query}.TW", None, []) if query.isdigit() else (None, None, [])

    entry = stocks[code]
    return f"{code}.{entry['suffix']}", entry["name"], []


def get_quote(symbol: str, displayName: str = None):
    """Fetch one quote. Returns None if the symbol is unknown to Yahoo."""
    response = requests.get(
        CHART_URL.format(symbol=symbol), headers=HEADERS, timeout=TIMEOUT
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()

    chart = response.json().get("chart") or {}
    if chart.get("error") or not chart.get("result"):
        return None

    meta = chart["result"][0]["meta"]
    price = meta.get("regularMarketPrice")
    previous = meta.get("previousClose") or meta.get("chartPreviousClose")
    if price is None or not previous:
        return None

    marketTime = meta.get("regularMarketTime")
    quotedAt = (
        datetime.fromtimestamp(marketTime, timezone.utc) if marketTime else None
    )

    change = price - previous
    changePercent = change / previous * 100

    return {
        "symbol": meta.get("symbol", symbol),
        "name": displayName or meta.get("longName") or meta.get("shortName") or symbol,
        "price": price,
        "previousClose": previous,
        "change": change,
        "changePercent": changePercent,
        "dayHigh": meta.get("regularMarketDayHigh"),
        "dayLow": meta.get("regularMarketDayLow"),
        "yearHigh": meta.get("fiftyTwoWeekHigh"),
        "yearLow": meta.get("fiftyTwoWeekLow"),
        "volume": meta.get("regularMarketVolume"),
        "currency": meta.get("currency", ""),
        "quotedAt": quotedAt,
        "isFresh": bool(quotedAt and datetime.now(timezone.utc) - quotedAt < FRESH_WINDOW),
        "isTaiwan": symbol.endswith(".TW") or symbol.endswith(".TWO"),
    }


def format_tw_time(momentUTC: datetime):
    return momentUTC.astimezone(TW).strftime("%m/%d %H:%M") if momentUTC else "—"


def limit_flag(quote: dict):
    """漲停 / 跌停 marker for Taiwan's 10% daily band."""
    if not quote["isTaiwan"]:
        return ""
    if quote["changePercent"] >= LIMIT_THRESHOLD:
        return " 🚀漲停"
    if quote["changePercent"] <= -LIMIT_THRESHOLD:
        return " 🧊跌停"
    return ""
