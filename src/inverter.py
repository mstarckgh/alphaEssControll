import logging
from dataclasses import dataclass
from typing import Optional
from pymodbus.client import ModbusTcpClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("AlphaESS")


@dataclass
class BatteryState:
    soc: float        # % (0.1/bit)
    soh: float        # % (0.1/bit)
    power: int        # W (-=Laden, +=Entladen)
    voltage: float    # V (0.1V/bit)
    current: float    # A (0.1A/bit, signed)
    temp_min: float   # °C (min cell temp, signed)
    temp_max: float   # °C (max cell temp, signed)
    capacity: float   # kWh (0.1kWh/bit)
    status: int       # Note1: charge/discharge state


@dataclass
class PVState:
    power_total: int  # W (sum PV1+PV2+PV3)
    pv1_power: int    # W (unsigned int)
    pv1_voltage: float
    pv1_current: float
    pv2_power: int
    pv2_voltage: float
    pv2_current: float
    pv3_power: int
    pv3_voltage: float
    pv3_current: float
    inv_temp: float   # °C (Wechselrichter-Temperatur, 0x0435)
    work_mode: int    # Note5


@dataclass
class GridState:
    power: int            # W (signed, Total Active Power)
    voltage: float        # V (Phase A, 1V/bit)
    frequency: float      # Hz (0.01Hz/bit)
    max_export_pct: int   # % (0=gesperrt, 100=voll)
    energy_feed: float    # kWh (total feed to grid, 0.01kWh/bit)
    energy_consume: float # kWh (total consume from grid, 0.01kWh/bit)


@dataclass
class DispatchState:
    active: bool
    power: int             # W (offset 32000 entfernt: <0=Laden, >0=Entladen)
    mode: int              # Note7
    soc_target: float      # % (0.4%/bit)
    remaining_seconds: int


@dataclass
class SystemState:
    inverter_sn: str
    fault_code: int


class AlphaESSInverter:
    """
    Modbus TCP Interface für Alpha ESS SMILE-T10-HV-INV
    Basierend auf: Alpha-Modbus-Protocol_V1_28
    Slave ID: 0x55 (85)
    """

    SLAVE = 0x55

    def __init__(self, host: str, port: int = 502):
        self.host = host
        self.port = port
        self._client = ModbusTcpClient(host, port=port)

    def connect(self) -> bool:
        result = self._client.connect()
        if result:
            log.info(f"Verbunden mit {self.host}:{self.port}")
        else:
            log.error(f"Verbindung zu {self.host}:{self.port} fehlgeschlagen")
        return result

    def disconnect(self):
        self._client.close()
        log.info("Verbindung getrennt")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    # ─── Interne Hilfsmethoden ────────────────────────────────────────────────

    def _read(self, address: int, count: int = 1) -> Optional[list]:
        r = self._client.read_holding_registers(
            address=address, count=count, slave=self.SLAVE
        )
        if r.isError():
            log.warning(f"Lesefehler Register 0x{address:04X}: {r}")
            return None
        return r.registers

    def _u32(self, regs: list, idx: int = 0) -> int:
        """Unsigned 32-bit aus zwei 16-bit Registern"""
        return (regs[idx] << 16) | regs[idx + 1]

    def _s16(self, val: int) -> int:
        """Signed 16-bit"""
        return val if val < 32768 else val - 65536

    def _s32(self, regs: list, idx: int = 0) -> int:
        """Signed 32-bit aus zwei 16-bit Registern"""
        raw = (regs[idx] << 16) | regs[idx + 1]
        return raw if raw < 0x80000000 else raw - 0x100000000

    # ─── Batterie (0x0100-0x0126) ─────────────────────────────────────────────

    def get_battery(self) -> Optional[BatteryState]:
        # Lese Block 0x0100-0x0126 (39 Register, inkl. Battery Power an 0x0126)
        r = self._read(0x0100, count=39)
        if r is None:
            log.error("Batterie: Lesefehler")
            return None

        return BatteryState(
            voltage  = r[0x0100 - 0x0100] / 10.0,
            current  = self._s16(r[0x0101 - 0x0100]) / 10.0,
            soc      = r[0x0102 - 0x0100] / 10.0,
            status   = r[0x0103 - 0x0100],
            temp_min = self._s16(r[0x010D - 0x0100]) / 10.0,
            temp_max = self._s16(r[0x0110 - 0x0100]) / 10.0,
            capacity = r[0x0119 - 0x0100] / 10.0,
            soh      = r[0x011B - 0x0100] / 10.0,
            power    = self._s16(r[0x0126 - 0x0100]),  # -=Laden, +=Entladen
        )

    # ─── PV / Wechselrichter (0x041C-0x0440) ──────────────────────────────────

    def get_pv(self) -> Optional[PVState]:
        # Lese Block 0x041C-0x0440 (37 Register)
        r = self._read(0x041C, count=37)
        if r is None:
            log.error("PV: Lesefehler")
            return None

        base = 0x041C

        freq    = r[0x041C - base]               # Inverter Grid Frequency
        pv1_v   = r[0x041D - base] / 10.0
        pv1_i   = r[0x041E - base] / 10.0
        pv1_p   = self._u32(r, 0x041F - base)
        pv2_v   = r[0x0421 - base] / 10.0
        pv2_i   = r[0x0422 - base] / 10.0
        pv2_p   = self._u32(r, 0x0423 - base)
        pv3_v   = r[0x0425 - base] / 10.0
        pv3_i   = r[0x0426 - base] / 10.0
        pv3_p   = self._u32(r, 0x0427 - base)
        inv_temp = r[0x0435 - base] / 10.0
        mode    = r[0x0440 - base]

        return PVState(
            power_total = pv1_p + pv2_p + pv3_p,
            pv1_power   = pv1_p,
            pv1_voltage = pv1_v,
            pv1_current = pv1_i,
            pv2_power   = pv2_p,
            pv2_voltage = pv2_v,
            pv2_current = pv2_i,
            pv3_power   = pv3_p,
            pv3_voltage = pv3_v,
            pv3_current = pv3_i,
            inv_temp    = inv_temp,
            work_mode   = mode,
        )

    # ─── Netz (Grid Meter 0x0010-0x0022) ─────────────────────────────────────

    def get_grid(self) -> Optional[GridState]:
        energy  = self._read(0x0010, count=4)   # 0x0010-0x0013 energy counters
        voltage = self._read(0x0014, count=1)   # Phase A voltage, 1V/bit
        freq    = self._read(0x001A, count=1)   # Frequency, 0.01Hz/bit
        power   = self._read(0x0021, count=2)   # Total Active Power, signed 32-bit
        cfg     = self._read(0x0800, count=1)   # MAX Feed into grid percent

        if any(v is None for v in [energy, voltage, freq, power, cfg]):
            log.error("Netz: Lesefehler")
            return None

        return GridState(
            energy_feed    = self._u32(energy, 0) * 0.01,
            energy_consume = self._u32(energy, 2) * 0.01,
            voltage        = voltage[0],
            frequency      = freq[0] / 100.0,
            power          = self._s32(power, 0),
            max_export_pct = cfg[0],
        )

    # ─── Dispatch (0x0880-0x0888) ────────────────────────────────────────────

    def get_dispatch(self) -> Optional[DispatchState]:
        r = self._read(0x0880, count=9)
        if r is None:
            log.error("Dispatch: Lesefehler")
            return None

        raw_power = self._u32(r, 1)  # 0x0881/0x0882

        return DispatchState(
            active            = bool(r[0]),
            power             = raw_power - 32000,
            mode              = r[5],               # 0x0885
            soc_target        = r[6] * 0.4,         # 0x0886
            remaining_seconds = self._u32(r, 7),    # 0x0887/0x0888
        )

    # ─── System Info ─────────────────────────────────────────────────────────

    def get_system(self) -> Optional[SystemState]:
        # Inverter SN: 0x064A~0x0653 (10 Register = 20 bytes ASCII)
        sn_regs = self._read(0x064A, count=10)
        fault   = self._read(0x0701, count=2)

        if sn_regs is None:
            log.warning("Inverter SN nicht lesbar – versuche EMS SN (0x0706)")
            sn_regs = self._read(0x0706, count=8)

        sn = ""
        if sn_regs:
            for reg in sn_regs:
                hi = (reg >> 8) & 0xFF
                lo = reg & 0xFF
                if hi: sn += chr(hi)
                if lo: sn += chr(lo)
            sn = sn.strip("\x00").strip()

        fault_code = self._u32(fault, 0) if fault else 0

        return SystemState(
            inverter_sn = sn,
            fault_code  = fault_code,
        )

    # ─── Steuerung ───────────────────────────────────────────────────────────

    def set_max_export(self, percent: int) -> bool:
        """Netzeinspeisung begrenzen: 0=sperren, 100=voll erlaubt (0x0800)"""
        percent = max(0, min(100, percent))
        r = self._client.write_register(
            address=0x0800, value=percent, slave=self.SLAVE
        )
        if r.isError():
            log.error(f"set_max_export({percent}%) fehlgeschlagen")
            return False
        log.info(f"Max Einspeisung → {percent}%")
        return True

    def set_dispatch(self, power_w: int, duration_s: int, mode: int = 5) -> bool:
        """
        Dispatch setzen (0x0880-0x0888).
        power_w > 0 = Entladen (raw > 32000)
        power_w < 0 = Laden    (raw < 32000)
        power_w = 0 = Stop
        mode 5 = Normal Mode (empfohlen laut Doku)
        Reihenfolge: Mode → Power → Time → Start (Start immer zuletzt!)
        """
        if power_w == 0:
            return self.stop_dispatch()

        raw = 32000 + power_w
        raw = max(0, min(65535, raw))
        hi = (raw >> 16) & 0xFFFF
        lo = raw & 0xFFFF

        self._client.write_register(address=0x0885, value=mode,       slave=self.SLAVE)
        self._client.write_register(address=0x0881, value=hi,         slave=self.SLAVE)
        self._client.write_register(address=0x0882, value=lo,         slave=self.SLAVE)
        self._client.write_register(address=0x0887, value=0,          slave=self.SLAVE)
        self._client.write_register(address=0x0888, value=duration_s, slave=self.SLAVE)
        r = self._client.write_register(address=0x0880, value=1,      slave=self.SLAVE)

        if r.isError():
            log.error("set_dispatch fehlgeschlagen")
            return False
        log.info(f"Dispatch: {power_w:+}W für {duration_s}s (Modus {mode})")
        return True

    def stop_dispatch(self) -> bool:
        """Dispatch stoppen (0x0880 = 0)"""
        r = self._client.write_register(address=0x0880, value=0, slave=self.SLAVE)
        if r.isError():
            log.error("stop_dispatch fehlgeschlagen")
            return False
        log.info("Dispatch gestoppt")
        return True
