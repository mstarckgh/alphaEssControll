import logging
import pymysql
from datetime import datetime
from typing import Optional
from inverter import BatteryState, PVState, GridState

log = logging.getLogger("AlphaDB")

class AlphaDB:
    def __init__(
        self,
        host: str = "localhost",
        user: str = "alphaess",
        password: str = "alphaess123",
        db: str = "alphaess",
    ):
        self.config = dict(host=host, user=user, password=password,
                           db=db, charset="utf8mb4", autocommit=True)
        self._conn = None

    def connect(self):
        self._conn = pymysql.connect(**self.config)
        log.info("DB connected")

    def disconnect(self):
        if self._conn:
            self._conn.close()
            log.info("DB disconnected")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    def _cursor(self):
        if self._conn is None:
            raise RuntimeError("Keine DB Verbindung")
        self._conn.ping(reconnect=True)
        return self._conn.cursor()

    # ─── Wechselrichter Status ────────────────────────────────────────────────

    def save_inverter_status(
        self,
        battery: Optional[BatteryState],
        pv: Optional[PVState],
        grid: Optional[GridState],
    ):
        sql = """
            INSERT INTO inverter_status (
                bat_soc, bat_soh, bat_status, bat_power_w,
                bat_voltage_v, bat_current_a, bat_temp_min_c, bat_temp_max_c,
                pv_power_w, pv1_voltage_v, pv1_current_a, pv1_power_w,
                pv2_voltage_v, pv2_current_a, pv2_power_w,
                pv3_voltage_v, pv3_current_a, pv3_power_w,
                inv_temp_c, inv_work_mode,
                grid_power_w, grid_voltage_v, grid_freq_hz,
                grid_energy_feed_kwh, grid_energy_consume_kwh, grid_export_pct
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s
            )
        """
        values = (
            battery.soc        if battery else None,
            battery.soh        if battery else None,
            battery.status     if battery else None,
            battery.power      if battery else None,
            battery.voltage    if battery else None,
            battery.current    if battery else None,
            battery.temp_min   if battery else None,
            battery.temp_max   if battery else None,
            pv.power_total     if pv else None,
            pv.pv1_voltage     if pv else None,
            pv.pv1_current     if pv else None,
            pv.pv1_power       if pv else None,
            pv.pv2_voltage     if pv else None,
            pv.pv2_current     if pv else None,
            pv.pv2_power       if pv else None,
            pv.pv3_voltage     if pv else None,
            pv.pv3_current     if pv else None,
            pv.pv3_power       if pv else None,
            pv.inv_temp        if pv else None,
            pv.work_mode       if pv else None,
            grid.power         if grid else None,
            grid.voltage       if grid else None,
            grid.frequency     if grid else None,
            grid.energy_feed   if grid else None,
            grid.energy_consume if grid else None,
            grid.max_export_pct if grid else None,
        )
        with self._cursor() as c:
            c.execute(sql, values)
        log.info("Inverter-Status gespeichert")

    # ─── Strompreise ─────────────────────────────────────────────────────────

    def save_prices(self, entries: list[dict]):
        sql = """
            INSERT IGNORE INTO prices (ts_start, ts_end, price_ct)
            VALUES (%s, %s, %s)
        """
        with self._cursor() as c:
            for e in entries:
                c.execute(sql, (e["start"], e["end"], e["price_ct"]))
        log.info(f"{len(entries)} Preiseinträge gespeichert")

    def get_current_price(self) -> Optional[float]:
        sql = """
            SELECT price_ct FROM prices
            WHERE ts_start <= NOW() AND ts_end > NOW()
            ORDER BY ts_start DESC LIMIT 1
        """
        with self._cursor() as c:
            c.execute(sql)
            row = c.fetchone()
        return row[0] if row else None

    def get_upcoming_prices(self, hours: int = 24) -> list[dict]:
        sql = """
            SELECT ts_start, ts_end, price_ct FROM prices
            WHERE ts_end > NOW()
            ORDER BY ts_start ASC
            LIMIT %s
        """
        with self._cursor() as c:
            c.execute(sql, (hours,))
            rows = c.fetchall()
        return [{"start": r[0], "end": r[1], "price_ct": r[2]} for r in rows]

    # ─── Steuerungsaktionen ───────────────────────────────────────────────────

    def log_action(self, action: str, reason: str = "", value: float = None):
        sql = """
            INSERT INTO control_actions (action, reason, value)
            VALUES (%s, %s, %s)
        """
        with self._cursor() as c:
            c.execute(sql, (action, reason, value))
        log.info(f"Aktion gespeichert: {action} ({reason})")
