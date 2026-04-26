from pymodbus.client import ModbusTcpClient


IP_ADDRESS = "192.168.178.31"
PORT = 502
MODBUS_SLAVE_ADDRESS = 0x55

c = ModbusTcpClient(IP_ADDRESS, port=PORT)
c.connect()


def read(addr, count=1, label=""):
    r = c.read_holding_registers(address=addr, count=count, slave=MODBUS_SLAVE_ADDRESS)

    if not r.isError():
        print(f"✅ 0x{addr:04X} {label}: {r.registers}")
    else:
        print(f"❌ 0x{addr:04X} {label}: kein Wert")


read(0x0880, 1, "Dispatch Start")
read(0x0881, 2, "Dispatch Leistung (W)")
read(0x0885, 1, "Dispatch Modus")
read(0x0887, 2, "Dispatch Zeit (s)")
read(0x0800, 1, "Max Einspeisung % (0=sperren!)")

c.close()
