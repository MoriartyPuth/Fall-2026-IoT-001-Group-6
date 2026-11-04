"""Fake ESP32: runs the same edge logic as esp32/main.py on synthetic sensor
readings and POSTs the packets to Node-RED. Use it to test the pipeline and
Grafana before the board is connected.

    python3 tools/simulate.py                 # loop SAFE -> WARNING -> DANGER, fever on/off
    python3 tools/simulate.py --count 30      # stop after 30 packets
    python3 tools/simulate.py --url http://localhost:1880/lab4/data
"""
import argparse
import json
import math
import pathlib
import random
import sys
import time
import urllib.request

ESP32_DIR = pathlib.Path(__file__).resolve().parent.parent  # lab4/ (main.py + lib/)
sys.path[:0] = [str(ESP32_DIR), str(ESP32_DIR / "lib")]
import main as edge  # noqa: E402  (edge logic from the real firmware)
from bmp280 import altitude_m  # noqa: E402


def gas_profile(step):
    # 90-sample cycle: clean air -> gas leak -> clear
    phase = step % 90
    if phase < 30:
        base = 1500
    elif phase < 45:
        base = 1500 + (phase - 30) * 90   # ramps into WARNING / DANGER
    elif phase < 60:
        base = 2900
    else:
        base = max(1500, 2900 - (phase - 60) * 110)
    return int(min(4095, max(0, base + random.gauss(0, 120))))


def body_profile(step):
    # alternate normal (~31 C) and fever (~34 C) every 40 samples
    target = 34.0 if (step // 40) % 2 else 31.0
    return target + random.gauss(0, 0.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:1880/lab4/data")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--count", type=int, default=0, help="0 = forever")
    args = ap.parse_args()

    buffer = []
    step = 0
    while args.count == 0 or step < args.count:
        gas_raw = gas_profile(step)
        gas_avg = edge.moving_average(buffer, gas_raw)
        body = body_profile(step)
        pressure = 1009.5 + 0.8 * math.sin(step / 40) + random.gauss(0, 0.05)
        altitude = altitude_m(pressure)
        lt = time.localtime()
        stamp = edge.iso_timestamp(tuple(lt[:6]), edge.config.TZ_OFFSET_HOURS)

        packet = edge.build_packet(gas_raw, gas_avg, body, 29.0 + random.gauss(0, 0.1),
                                   30.5 + random.gauss(0, 0.1), pressure, altitude, stamp)
        packet["device"] = "simulator"

        req = urllib.request.Request(args.url, data=json.dumps(packet).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            code = resp.status
        print("%s | GAS raw=%4d avg=%7.1f %-7s | BODY %.2f C fever=%d | P %.2f hPa ALT %.1f m -> %d" % (
            stamp, gas_raw, gas_avg, packet["risk_level"], packet["body_temp"],
            packet["fever_flag"], packet["pressure"], packet["altitude"], code))
        step += 1
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
