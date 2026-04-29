from pymodbus.client import ModbusTcpClient, ModbusTlsClient
import urllib.request
import json
from datetime import datetime, timezone

INVERTER_IP = "192.168.178.31"
SLAVE_ID = 0x55

# Schwellwerte
PREIS_NEGATIV   = 0.0   # ct/kWh - Entladung sperren, ggf aus Netz laden
PREIS_GUENSTIG  = 5.0   # ct/kWh - normal Self-Consumption
PREIS_TEUER     = 15.0  # ct/kWh - Entladung maximieren


def get_current_price():
    url = "https://api.awattar.de/v1/marketdata"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    now = datetime.now(tz=timezone.utc)
    for entry in data["data"]:
        start = datetime.fromtimestamp(entry["start_timestamp"]/1000, tz=timezone.utc)
        end   = datetime.fromtimestamp(entry["end_timestamp"]/1000,   tz=timezone.utc)
        if start <= now <= end:
            return entry["marketprice"] / 10  # → ct/kWh
    return None

def get_soc(client:ModbusTlsClient):
    r = client.read_holding_registers(address=0x0102, count=2, slave=SLAVE_ID)
    if not r.isError():
        return r.registers[0] / 10.0
    return None

def set_export(client:ModbusTlsClient, percent:int):
    # Einspeisung begrenzen: 0=sperren, 100=voll erlauben
    client.write_register(address=0x0800, value=percent, slave=SLAVE_ID)
    print(f"  → Max Einspeisung gesetzt auf {percent}%")

def run():
    preis = get_current_price()
    if preis is None:
        print("❌ Preis konnte nicht abgerufen werden")
        return

    now = datetime.now().strftime("%d.%m %H:%M")
    print(f"\n[{now}] Aktueller Preis: {preis:.2f} ct/kWh")

    c = ModbusTcpClient(INVERTER_IP, port=502)
    c.connect()

    soc = get_soc(c)
    print(f" Batterie SOC: {soc}%")

    if preis < PREIS_NEGATIV:
        print("  🚨 NEGATIVER PREIS - Sperre Einspeisung!")
        set_export(c, 0)
    elif preis < PREIS_GUENSTIG:
        print("  🟢 Günstiger Preis - Normal")
        set_export(c, 100)
    elif preis > PREIS_TEUER:
        print("  🔴 Teurer Strom - Einspeisung erlaubt")
        set_export(c, 100)
    else:
        print("  🟡 Normaler Preis - Self-Consumption")
        set_export(c, 100)

    c.close()


if __name__ == "__main__":
    run()

