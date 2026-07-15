"""Fetch East Money LHB daily list for a given date."""
import json
import sys
import urllib.request

DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-06-23"
url = (
    "https://datacenter-web.eastmoney.com/api/data/v1/get?"
    "sortColumns=SECURITY_CODE,TRADE_DATE&sortTypes=1,-1&pageSize=500&pageNumber=1"
    "&reportName=RPT_DAILYBILLBOARD_DETAILS"
    "&columns=SECURITY_CODE,SECUCODE,SECURITY_NAME_ABBR,TRADE_DATE,EXPLAIN,CLOSE_PRICE,"
    "CHANGE_RATE,TURNOVERRATE"
    f"&source=WEB&client=WEB&filter=(TRADE_DATE='{DATE}')"
)
req = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://data.eastmoney.com/",
    },
)
data = json.loads(urllib.request.urlopen(req, timeout=30).read())
rows = data.get("result", {}).get("data", [])
print("count", len(rows))
for r in rows:
    print(
        r["SECURITY_CODE"],
        r["SECURITY_NAME_ABBR"],
        r["CHANGE_RATE"],
        r.get("EXPLAIN", "")[:100],
        r.get("TURNOVERRATE", ""),
    )
