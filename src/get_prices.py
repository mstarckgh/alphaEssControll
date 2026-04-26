import urllib.request
import json
from datetime import datetime, timezone


# SMARD API - Großhandelspreise Deutschlande (EPEX Day-Ahead)
url = "http://www.smard.de/app/chart_data/4169/DE4169_DE_hour_1.json"

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read())

# Letzten 5 einträge
series = data["series"]
print("Letzte Strompreise (EPEX Day-Ahead, €/MWh): \n")
for ts, price in series[-5:]:
    if price is not None:
        dt = datetime.fromtimestamp(ts/1000, tz=timezone.utc).astimezone()
        # €/MWh → Cent/kWh
        cent_kwh = price / 10
        print(f"{dt.strftime('%d.%m %H:%M')} Uhr: {cent_kwh:.2f} ct/kWh", end="")
        if cent_kwh < 0:
            print(" ⚠️  NEGATIVER PREIS!")
        elif cent_kwh < 5:
            print(" 🟢 sehr günstig")
        elif cent_kwh > 20:
            print(" 🔴 teuer")
        else:
            print()

