from src.database import AlphaDB
from src.inverter import AlphaESSInverter

with AlphaDB() as db:
    # Preise laden und speichern
    import urllib.request, json
    from datetime import datetime, timezone
    url = "https://api.awattar.de/v1/marketdata"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())

    entries = [
        {
            "start":    datetime.fromtimestamp(e["start_timestamp"]/1000, tz=timezone.utc),
            "end":      datetime.fromtimestamp(e["end_timestamp"]/1000,   tz=timezone.utc),
            "price_ct": e["marketprice"] / 10,
        }
        for e in data["data"]
    ]
    db.save_prices(entries)

    # Aktuellen Preis lesen
    preis = db.get_current_price()
    print(f"Aktueller Preis aus DB: {preis:.2f} ct/kWh")

    # Wechselrichter auslesen und speichern
    with AlphaESSInverter("192.168.178.31") as inv:
        bat  = inv.get_battery()
        pv   = inv.get_pv()
        grid = inv.get_grid()
        db.save_inverter_status(bat, pv, grid)

    # Aktion loggen
    db.log_action("test", "Erster DB-Test", 0)

    print("Alles gespeichert ✅")
