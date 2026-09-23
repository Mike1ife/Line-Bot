"""Build data/tw_stocks.json: Taiwan ticker -> Chinese name.

Run occasionally (new listings are rare), never at request time - both TWSE
endpoints take seconds, which is far too slow for a LINE reply.

    python -m tools.build_stock_names
"""

import io
import json
import re
import requests

TSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
OTC_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
OUTPUT = "data/tw_stocks.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}
# STOCK_DAY_ALL is used rather than BWIBBU_ALL because the latter is the
# PE/yield report and therefore omits ETFs, which are household names here
# (0050, 0056, 00878). 4-6 digits covers shares and ETFs while excluding
# warrants and bonds, whose codes carry letters.
CODE_PATTERN = re.compile(r"^\d{4,6}$")


def build():
    stocks = {}

    listed = requests.get(TSE_URL, headers=HEADERS, timeout=60).json()
    for row in listed:
        code, name = row.get("Code", "").strip(), row.get("Name", "").strip()
        if CODE_PATTERN.match(code) and name:
            stocks[code] = {"name": name, "suffix": "TW"}

    otc = requests.get(OTC_URL, headers=HEADERS, timeout=60).json()
    for row in otc:
        code = row.get("SecuritiesCompanyCode", "").strip()
        name = row.get("CompanyName", "").strip()
        if CODE_PATTERN.match(code) and name and code not in stocks:
            stocks[code] = {"name": name, "suffix": "TWO"}

    with io.open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(stocks, f, ensure_ascii=False, indent=0, sort_keys=True)

    listedCount = sum(1 for v in stocks.values() if v["suffix"] == "TW")
    print(f"{OUTPUT}: {len(stocks)} tickers ({listedCount} 上市 / "
          f"{len(stocks) - listedCount} 上櫃)")


if __name__ == "__main__":
    build()
