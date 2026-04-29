from pymodbus.client import ModbusTcpClient

c = ModbusTcpClient('192.168.178.31', port=502)
c.connect()

bereiche = [
    (0x0000, 0x0030, "System/PV"),
    (0x0060, 0x0090, "Temperatur/Frequenz"),
    (0x0100, 0x0130, "Batterie"),
    (0x0150, 0x0170, "Batterie erweitert"),
]

for start, end, name in bereiche:
    print(f"\n── {name} (0x{start:04X} - 0x{end:04X}) ──")
    for addr in range(start, end, 4):
        r = c.read_holding_registers(address=addr, count=4, slave=0x55)
        if not r.isError():
            vals = r.registers
            if any(v != 0 for v in vals):  # nur nicht-null Werte
                for i, v in enumerate(vals):
                    print(f"  0x{addr+i:04X}: {v:6d}  ({v/10:8.1f})")

c.close()
