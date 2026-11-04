# LAB 4 - Multi-Sensor IoT Monitoring (ESP32 + MicroPython)
#
# Sensors (I2C bus: SDA = GPIO21, SCL = GPIO22)
#   MLX90614  body temperature        0x5A
#   BMP280    room temp + pressure    0x76 / 0x77
#   DS3231    real-time clock         0x68
# Analog
#   MQ-5      gas sensor A0           GPIO33 (ADC1, 12-bit)
#
# Edge logic before sending to Node-RED:
#   1. gas moving average over the last 5 samples
#   2. gas risk: SAFE / WARNING / DANGER
#   3. fever flag from body temperature
#   4. pressure + altitude sent as-is
#   5. timestamp taken from the DS3231

import json
import time

import config

GAS_WINDOW = 5
GAS_WARNING = 2100   # avg >= 2100 -> WARNING
GAS_DANGER = 2600    # avg >= 2600 -> DANGER
FEVER_C = 32.5       # body_temp >= 32.5 C -> fever_flag = 1

gas_buffer = []


# ---------------- edge logic ----------------

def moving_average(buffer, value, window=GAS_WINDOW):
    buffer.append(value)
    if len(buffer) > window:
        buffer.pop(0)
    return sum(buffer) / len(buffer)


def classify_gas(avg):
    """Return (risk_level, risk_code)."""
    if avg >= GAS_DANGER:
        return "DANGER", 2
    if avg >= GAS_WARNING:
        return "WARNING", 1
    return "SAFE", 0


def fever_flag(body_temp):
    if body_temp is not None and body_temp >= FEVER_C:
        return 1
    return 0


def iso_timestamp(dt, tz_hours):
    year, month, day, hour, minute, second = dt[:6]
    sign = "+" if tz_hours >= 0 else "-"
    return "%04d-%02d-%02dT%02d:%02d:%02d%s%02d:00" % (
        year, month, day, hour, minute, second, sign, abs(tz_hours))


def r(value, digits=2):
    return None if value is None else round(value, digits)


def build_packet(gas_raw, gas_avg, body_temp, ambient_temp,
                 room_temp, pressure, altitude, timestamp):
    risk_level, risk_code = classify_gas(gas_avg)
    return {
        "device": config.DEVICE_ID,
        "gas_raw": gas_raw,
        "gas_avg": r(gas_avg, 1),
        "risk_level": risk_level,
        "risk_code": risk_code,
        "body_temp": r(body_temp),
        "ambient_temp": r(ambient_temp),
        "fever_flag": fever_flag(body_temp),
        "room_temp": r(room_temp),
        "pressure": r(pressure),
        "altitude": r(altitude, 1),
        "timestamp": timestamp,
    }


# ---------------- hardware ----------------

def try_init(name, factory):
    try:
        dev = factory()
        print("[ok]   %s" % name)
        return dev
    except Exception as e:
        print("[FAIL] %s: %s" % (name, e))
        return None


def connect_wifi(timeout_s=15):
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan
    print("Connecting to WiFi '%s' ..." % config.WIFI_SSID)
    try:
        wlan.disconnect()  # cancel any attempt still pending (e.g. after a soft reset)
    except OSError:
        pass
    try:
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    except OSError as e:
        print("WiFi connect error:", e)
        return wlan
    start = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout_s * 1000:
            print("WiFi connect timed out")
            wlan.disconnect()
            return wlan
        time.sleep_ms(250)
    print("WiFi connected, IP:", wlan.ifconfig()[0])
    return wlan


def sync_rtc(rtc):
    # ntptime sets the ESP32 clock to UTC; the DS3231 keeps local time
    import ntptime
    try:
        ntptime.settime()
        t = time.localtime(time.time() + config.TZ_OFFSET_HOURS * 3600)
        rtc.set_datetime(t[0], t[1], t[2], t[3], t[4], t[5], t[6] + 1)
        print("DS3231 set from NTP:", iso_timestamp(rtc.datetime(), config.TZ_OFFSET_HOURS))
    except Exception as e:
        print("NTP sync failed (keeping DS3231 time):", e)


def send(packet):
    try:
        import urequests as requests
    except ImportError:
        import requests
    try:
        resp = requests.post(config.NODE_RED_URL, data=json.dumps(packet),
                             headers={"Content-Type": "application/json"})
        status = resp.status_code
        resp.close()
        return status
    except Exception as e:
        print("  send failed:", e)
        return None


def run():
    import sys
    sys.path.insert(0, "/lib")  # use the drivers in /lib over any older copies in /
    from machine import ADC, I2C, Pin
    from bmp280 import BMP280, altitude_m
    from ds3231 import DS3231
    from mlx90614 import MLX90614

    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)  # MLX90614 max is 100 kHz
    print("I2C devices:", [hex(a) for a in i2c.scan()])

    adc = ADC(Pin(33))
    adc.atten(ADC.ATTN_11DB)  # full 0-3.3 V range
    try:
        adc.width(ADC.WIDTH_12BIT)
    except AttributeError:
        pass

    mlx = try_init("MLX90614", lambda: MLX90614(i2c))
    bmp = try_init("BMP280", lambda: BMP280(i2c))
    rtc = try_init("DS3231", lambda: DS3231(i2c))

    wlan = connect_wifi()
    if rtc and wlan.isconnected() and (config.SYNC_RTC_FROM_NTP or rtc.lost_power()):
        sync_rtc(rtc)

    while True:
        # Task 1: gas raw + moving average
        gas_raw = adc.read()
        gas_avg = moving_average(gas_buffer, gas_raw)

        # Task 3: body temperature
        body_temp = ambient_temp = None
        if mlx:
            try:
                body_temp = mlx.object_temp()
                ambient_temp = mlx.ambient_temp()
            except OSError as e:
                print("  MLX90614 read error:", e)

        # Task 4: pressure + altitude
        room_temp = pressure = altitude = None
        if bmp:
            try:
                room_temp, pressure = bmp.read()
                altitude = altitude_m(pressure, config.SEA_LEVEL_HPA)
            except OSError as e:
                print("  BMP280 read error:", e)

        # DS3231 timestamp
        timestamp = None
        if rtc:
            try:
                timestamp = iso_timestamp(rtc.datetime(), config.TZ_OFFSET_HOURS)
            except OSError as e:
                print("  DS3231 read error:", e)

        packet = build_packet(gas_raw, gas_avg, body_temp, ambient_temp,
                              room_temp, pressure, altitude, timestamp)

        print("%s | GAS raw=%4d avg=%7.1f %-7s | BODY %s C fever=%d | P %s hPa ALT %s m" % (
            timestamp, gas_raw, gas_avg, packet["risk_level"],
            packet["body_temp"], packet["fever_flag"],
            packet["pressure"], packet["altitude"]))

        if not wlan.isconnected():
            wlan = connect_wifi()
        if wlan.isconnected():
            status = send(packet)
            if status != 200:
                print("  Node-RED responded:", status)

        time.sleep_ms(config.SEND_INTERVAL_MS)


if __name__ == "__main__":
    run()
