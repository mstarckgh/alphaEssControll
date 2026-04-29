from pymodbus.client import ModbusTcpClient

c = ModbusTcpClient('192.168.178.31', port=502)
c.connect()

for addr, label in [
    (0x00a1, "0x0011"),
    (0x00a9, "0x0012"),
    (0x0102, "0x0013"),
]:
    r = c.read_holding_registers(address=addr, count=2, slave=0x55)
    if not r.isError():
        print(f"{label}: roh={r.registers} → /10={r.registers[0]/10:.1f}W")

c.close()
