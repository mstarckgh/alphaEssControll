from src.inverter import AlphaESSInverter

with AlphaESSInverter('192.168.178.31') as inv:
    inv.set_max_export(100)
