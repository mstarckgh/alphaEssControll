from pymodbus.client import ModbusTcpClient
import time


c = ModbusTcpClient("192.168.178.31", port=502)
c.connect()


def read(addr, count=1, label=""):
    r = c.read_holding_registers(address=addr, count=count, slave=0x55)
    if not r.isError():
        print(f"✅ {label}: {r.registers}")

# Vorher
read(0x0800, label="Max Einspeisung VORHER")

# Einspeisung sperren
print("\n⚡ Sperre Einspeisung ins Netz...")
c.write_register(address=0x0800, value=0, slave=0x55)
time.sleep(2)
read(0x0800, label="Max Einspeisung DANACH")

# Wieder freigeben
time.sleep(5)
print("\n✅ Gebe Einspeisung wieder frei...")
c.write_register(address=0x0800, value=100, slave=0x55)
time.sleep(1)
read(0x0800, label="Max Einspeisung WIEDERHERGESTELLT")

c.close()
