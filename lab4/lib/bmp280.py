# BMP280 / BME280 temperature + pressure sensor (I2C)
# Compensation formulas from the Bosch BMP280 datasheet, section 8.1 (floating point).
import struct
import time

_CHIP_IDS = (0x56, 0x57, 0x58, 0x60)  # 0x58 = BMP280, 0x60 = BME280


class BMP280:
    def __init__(self, i2c, addr=None):
        found = i2c.scan()
        if addr is None:
            addr = 0x76 if 0x76 in found else 0x77
        if addr not in found:
            raise OSError("BMP280 not found at 0x76/0x77")
        self.i2c = i2c
        self.addr = addr

        chip_id = i2c.readfrom_mem(addr, 0xD0, 1)[0]
        if chip_id not in _CHIP_IDS:
            raise OSError("unexpected BMP280 chip id 0x%02X" % chip_id)

        cal = i2c.readfrom_mem(addr, 0x88, 24)
        (self.t1, self.t2, self.t3,
         self.p1, self.p2, self.p3, self.p4, self.p5,
         self.p6, self.p7, self.p8, self.p9) = struct.unpack("<HhhHhhhhhhhh", cal)

        i2c.writeto_mem(addr, 0xF5, b"\x10")  # IIR filter x16, standby 0.5 ms
        i2c.writeto_mem(addr, 0xF4, b"\x57")  # temp x2, pressure x16, normal mode
        time.sleep_ms(100)

    def read(self):
        """Return (temperature_C, pressure_hPa)."""
        d = self.i2c.readfrom_mem(self.addr, 0xF7, 6)
        adc_p = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        adc_t = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)

        v1 = (adc_t / 16384.0 - self.t1 / 1024.0) * self.t2
        v2 = (adc_t / 131072.0 - self.t1 / 8192.0) ** 2 * self.t3
        t_fine = v1 + v2
        temp_c = t_fine / 5120.0

        v1 = t_fine / 2.0 - 64000.0
        v2 = v1 * v1 * self.p6 / 32768.0
        v2 = v2 + v1 * self.p5 * 2.0
        v2 = v2 / 4.0 + self.p4 * 65536.0
        v1 = (self.p3 * v1 * v1 / 524288.0 + self.p2 * v1) / 524288.0
        v1 = (1.0 + v1 / 32768.0) * self.p1
        if v1 == 0:
            raise OSError("BMP280 invalid calibration")
        p = 1048576.0 - adc_p
        p = (p - v2 / 4096.0) * 6250.0 / v1
        v1 = self.p9 * p * p / 2147483648.0
        v2 = p * self.p8 / 32768.0
        p = p + (v1 + v2 + self.p7) / 16.0
        return temp_c, p / 100.0


def altitude_m(pressure_hpa, sea_level_hpa=1013.25):
    # International barometric formula
    return 44330.0 * (1.0 - (pressure_hpa / sea_level_hpa) ** (1 / 5.255))
