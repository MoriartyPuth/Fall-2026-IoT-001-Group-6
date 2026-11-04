# MLX90614 infrared thermometer (I2C, SMBus, max 100 kHz)

_REG_AMBIENT = 0x06
_REG_OBJECT = 0x07


class MLX90614:
    def __init__(self, i2c, addr=0x5A):
        if addr not in i2c.scan():
            raise OSError("MLX90614 not found at 0x%02X" % addr)
        self.i2c = i2c
        self.addr = addr

    def _read_temp(self, reg):
        # 2 data bytes (LSB first) + PEC byte; resolution is 0.02 K per bit
        data = self.i2c.readfrom_mem(self.addr, reg, 3)
        raw = data[0] | (data[1] << 8)
        if raw & 0x8000:
            raise OSError("MLX90614 error flag set")
        return raw * 0.02 - 273.15

    def object_temp(self):
        return self._read_temp(_REG_OBJECT)

    def ambient_temp(self):
        return self._read_temp(_REG_AMBIENT)
