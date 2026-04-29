import logging
import urllib.request
import json
from pathlib import Path
from datetime import datetime, timezone

from inverter import AlphaESSInverter
from database import AlphaDB

# ─── Logging ─────────────────────────────────────────────────────────────────

LOG_FILE = Path(__file__).parent.parent / "logs" / "collector.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE),
    ]
)
log = logging.getLogger("Collector")

# ─── Config ──────────────────────────────────────────────────────────────────

INVERTER_IP = "192.168.178.31"

# ─── Preis-Abruf ─────────────────────────────────────────────────────────────

def fetch_prices(db: AlphaDB):
    """Preise von aWATTar abrufen und in DB speichern (ignoriert Duplikate)"""
    try:
        url = "https://api.awattar.de/v1/marketdata"
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaESS-Collector/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())

        entries = [
            {
                "start":    datetime.fromtimestamp(e["start_timestamp"] / 1000, tz=timezone.utc),
                "end":      datetime.fromtimestamp(e["end_timestamp"]   / 1000, tz=timezone.utc),
                "price_ct": e["marketprice"] / 10,
            }
            for e in data["data"]
        ]

        db.save_prices(entries)
        log.info(f"Preise aktualisiert: {len(entries)} Einträge")

    except Exception as e:
        log.error(f"Preisabruf fehlgeschlagen: {e}")

# ─── Hauptfunktion ────────────────────────────────────────────────────────────

def run():
    log.info("AlphaESS Collector läuft")

    with AlphaDB() as db:
        # Preise immer aktualisieren (DB ignoriert Duplikate via UNIQUE INDEX)
        fetch_prices(db)

        # Wechselrichter auslesen und steuern – alles in einer Verbindung
        with AlphaESSInverter(INVERTER_IP) as inv:
            bat  = inv.get_battery()
            pv   = inv.get_pv()
            grid = inv.get_grid()

            # Status in DB speichern
            db.save_inverter_status(bat, pv, grid)

            # Kompaktes Log
            soc    = f"{bat.soc:.1f}%"     if bat  else "?"
            power  = f"{bat.power:+}W"     if bat  else "?"
            pv_w   = f"{pv.power_total}W"  if pv   else "?"
            grid_w = f"{grid.power:+}W"    if grid else "?"
            exp    = f"{grid.max_export_pct}%" if grid else "?"
            log.info(f"SOC={soc} BAT={power} PV={pv_w} GRID={grid_w} EXPORT={exp}")

            # Preisbasierte Steuerung
            preis = db.get_current_price()
            if preis is None:
                log.warning("Kein aktueller Preis in DB – überspringe Steuerung")
                return

            if preis < 0 and grid is not None and grid.max_export_pct != 0:
                log.warning(f"Preis {preis:.2f} ct/kWh → Sperre Einspeisung!")
                inv.set_max_export(0)
                db.log_action("export_block", f"Negativpreis {preis:.2f} ct/kWh", 0)

            elif preis >= 0 and grid is not None and grid.max_export_pct == 0:
                log.info(f"Preis {preis:.2f} ct/kWh → Gebe Einspeisung frei")
                inv.set_max_export(100)
                db.log_action("export_allow", f"Preis positiv {preis:.2f} ct/kWh", 100)

            else:
                log.info(f"Preis {preis:.2f} ct/kWh → Keine Änderung nötig")


if __name__ == "__main__":
    run()
