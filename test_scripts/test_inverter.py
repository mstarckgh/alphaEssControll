from src.inverter import AlphaESSInverter

with AlphaESSInverter("192.168.178.31") as inv:
    print("\n🔋 Batterie:")
    b = inv.get_battery()
    if b:
        print(f"   SOC:       {b.soc:.1f}%")
        print(f"   SOH:       {b.soh:.1f}%")
        print(f"   Leistung:  {b.power:+}W  {'(Laden)' if b.power < 0 else '(Entladen)'}")
        print(f"   Spannung:  {b.voltage:.1f}V")
        print(f"   Strom:     {b.current:+.1f}A")
        print(f"   Temp min:  {b.temp_min:.1f}°C")
        print(f"   Temp max:  {b.temp_max:.1f}°C")
        print(f"   Kapazität: {b.capacity:.1f}kWh")
        print(f"   Status:    {b.status}")

    print("\n☀️  PV:")
    p = inv.get_pv()
    if p:
        print(f"   Gesamt:    {p.power_total}W")
        print(f"   PV1:       {p.pv1_power}W  ({p.pv1_voltage:.1f}V / {p.pv1_current:.1f}A)")
        print(f"   PV2:       {p.pv2_power}W  ({p.pv2_voltage:.1f}V / {p.pv2_current:.1f}A)")
        print(f"   PV3:       {p.pv3_power}W  ({p.pv3_voltage:.1f}V / {p.pv3_current:.1f}A)")
        print(f"   INV Temp:  {p.inv_temp:.1f}°C")
        print(f"   Modus:     {p.work_mode}")

    print("\n🔌 Netz:")
    g = inv.get_grid()
    if g:
        print(f"   Leistung:  {g.power:+}W  {'(Bezug)' if g.power > 0 else '(Einspeisung)'}")
        print(f"   Spannung:  {g.voltage:.0f}V")
        print(f"   Frequenz:  {g.frequency:.2f}Hz")
        print(f"   Export:    {g.max_export_pct}%  {'🔴 GESPERRT' if g.max_export_pct == 0 else '✅'}")
        print(f"   Eingespeist gesamt: {g.energy_feed:.1f}kWh")
        print(f"   Bezogen gesamt:     {g.energy_consume:.1f}kWh")

    print("\n⚡ Dispatch:")
    d = inv.get_dispatch()
    if d:
        print(f"   Aktiv:     {d.active}")
        print(f"   Leistung:  {d.power:+}W")
        print(f"   Modus:     {d.mode}")
        print(f"   Restzeit:  {d.remaining_seconds}s")

    print("\n🖥️  System:")
    s = inv.get_system()
    if s:
        print(f"   Seriennr:  {s.inverter_sn!r}")
        print(f"   Fehler:    {s.fault_code}")

