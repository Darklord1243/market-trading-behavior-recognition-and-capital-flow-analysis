"""Batch-fetch LHB seat details to UTF-8 JSON."""
import json
import sys
import time
import urllib.parse
import urllib.request

CODES = sys.argv[1:] if len(sys.argv) > 1 else []
DATE = "2026-06-23"
OUT = "scripts/lhb_0623_seats.json"


def fetch(report: str, sort_col: str, code: str) -> list:
    filt = f'(SECURITY_CODE="{code}")(TRADE_DATE=\'{DATE}\')'
    params = {
        "reportName": report,
        "columns": "ALL",
        "pageSize": "50",
        "pageNumber": "1",
        "sortColumns": sort_col,
        "sortTypes": "-1",
        "source": "WEB",
        "client": "WEB",
        "filter": filt,
    }
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get?" + urllib.parse.urlencode(params)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://data.eastmoney.com/stock/lhb,2026-06-23,{code}.html",
    }
    req = urllib.request.Request(url, headers=headers)
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return data.get("result", {}).get("data", []) or []


def pull(code: str) -> dict:
    time.sleep(0.8)
    return {
        "code": code,
        "meta": fetch("RPT_DAILYBILLBOARD_DETAILS", "SECURITY_CODE", code),
        "buy": fetch("RPT_BILLBOARD_DAILYDETAILSBUY", "BUY", code),
        "sell": fetch("RPT_BILLBOARD_DAILYDETAILSSELL", "SELL", code),
    }


results = []
for code in CODES:
    try:
        results.append(pull(code))
        print(f"ok {code}", flush=True)
    except Exception as exc:
        print(f"fail {code}: {exc}", flush=True)
        results.append({"code": code, "error": str(exc)})

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"wrote {OUT}")
