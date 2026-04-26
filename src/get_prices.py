import urllib.request
import json
from datetime import datetime, timezone

# aWATTar API - EPEX Day-Ahead Preise Deutschland
url = "https://api.awattar.de/v1/marketdata"

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read())

print("Aktuelle Strompreise (EPEX Day-Ahead, Brutto ct/kWh):\n")
now = datetime.now(tz=timezone.utc)

for entry in data["data"]:
    start = datetime.fromtimestamp(entry["start_timestamp"]/1000, tz=timezone.utc).astimezone()
    end   = datetime.fromtimestamp(entry["end_timestamp"]/1000,   tz=timezone.utc).astimezone()
    # aWATTar gibt €/MWh → Cent/kWh
    cent  = entry["marketprice"] / 10

    marker = " ← JETZT" if start <= now <= end else ""
    icon = "⚠️ NEGATIV" if cent < 0 else ("🟢" if cent < 5 else ("🟡" if cent < 15 else "🔴"))
    print(f"{start.strftime('%d.%m %H:%M')}-{end.strftime('%H:%M')}: {cent:6.2f} ct/kWh {icon}{marker}")

