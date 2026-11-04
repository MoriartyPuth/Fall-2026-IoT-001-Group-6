# DS3231 real-time clock (I2C address 0x68), registers are BCD encoded

_ADDR = 0x68
_REG_TIME = 0x00
_REG_STATUS = 0x0F


def _bcd2dec(b):
    return (b >> 4) * 10 + (b & 0x0F)


def _dec2bcd(d):
    return ((d // 10) << 4) | (d % 10)


class DS3231:
    def __init__(self, i2c, addr=_ADDR):
        if addr not in i2c.scan():
            raise OSError("DS3231 not found at 0x%02X" % addr)
        self.i2c = i2c
        self.addr = addr

    def datetime(self):
        """Return (year, month, day, hour, minute, second, weekday)."""
        d = self.i2c.readfrom_mem(self.addr, _REG_TIME, 7)
        second = _bcd2dec(d[0] & 0x7F)
        minute = _bcd2dec(d[1] & 0x7F)
        if d[2] & 0x40:  # 12-hour mode
            hour = _bcd2dec(d[2] & 0x1F) % 12
            if d[2] & 0x20:
                hour += 12
        else:
            hour = _bcd2dec(d[2] & 0x3F)
        weekday = d[3] & 0x07
        day = _bcd2dec(d[4] & 0x3F)
        month = _bcd2dec(d[5] & 0x1F)
        year = 2000 + _bcd2dec(d[6])
        return (year, month, day, hour, minute, second, weekday)

    def set_datetime(self, year, month, day, hour, minute, second, weekday=1):
        self.i2c.writeto_mem(self.addr, _REG_TIME, bytes((
            _dec2bcd(second), _dec2bcd(minute), _dec2bcd(hour),  # 24-hour mode
            weekday, _dec2bcd(day), _dec2bcd(month), _dec2bcd(year % 100),
        )))
        # clear the oscillator-stop flag so lost_power() reports False
        status = self.i2c.readfrom_mem(self.addr, _REG_STATUS, 1)[0]
        self.i2c.writeto_mem(self.addr, _REG_STATUS, bytes((status & 0x7F,)))

    def lost_power(self):
        return bool(self.i2c.readfrom_mem(self.addr, _REG_STATUS, 1)[0] & 0x80)
