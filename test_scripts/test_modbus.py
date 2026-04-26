from pymodbus.client import ModbusTcpClient
import pymodbus


print(pymodbus.__version__)

c = ModbusTcpClient('192.168.178.31', port=502)
print("Verbunden:", c.connect())

def read(address, count=2, label=""):
    r = c.read_holding_registers(address=address, count=count, slave=0x55)
    if not r.isError():
        print(f"{label}: {r.registers}")
    else:
        print(f"{label}: {Fehler}")

read(0x0102, 2, "SOC (Batterieladung)")
read(0x0100, 2, "Batterieleistung (W)")
read(0x0012, 2, "PV Leistung (W)")
read(0x0020, 1, "Dispatch Modus")
read(0x0024, 1, "Min SOC")
read(0x0025, 1, "Max SOC")

c.close()
