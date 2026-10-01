# Task 5 - Complete Smart Gate (ESP32 / MicroPython)
# One program: IR, servo, TM1637 and Blynk Automatic/Manual mode.
import time
import machine
import network
import _thread
try:
    import urequests as requests
except ImportError:
    import requests
try:
    import ujson as json
except ImportError:
    import json

# Credentials copied from your Task 2 gist. Edit here if they change.
WIFI_SSID = 'Robotic WIFI'
WIFI_PASS = 'rbtWIFI@2025'
BLYNK_TOKEN = 'P1xcNguUUzvQ64dApUEKsWmYlnJxHCOM'
# Use your regional server hostname from Blynk Console if necessary.
BLYNK_API = "https://blynk.cloud/external/api"
CLOUD_POLL_MS = 500
RESEND_MS = 10000

IR_PIN = 12
IR_ACTIVE_LEVEL = 0
DEBOUNCE_MS = 50
TM_CLK_PIN = 18
TM_DIO_PIN = 19
TM_BRIGHTNESS = 3
# Both displays wrap together from 9999 to 0 and reset on reboot.
COUNTER_MODULUS = 10000

SERVO_PIN = 13
CLOSED_ANGLE = 0
OPEN_ANGLE = 90
OPEN_TIME_MS = 2000
DUTY_MIN = 26
DUTY_MAX = 128
# V2: IR string; V3: slider; V4: count; V5: mode; V6: servo angle.
# Mode switch: 1 = Automatic, 0 = Manual. Boot starts in Automatic.
TELEMETRY = (("V2", "status"), ("V4", "count"), ("V6", "angle"))


def poll_controls():
    # Each read can fail independently; retain the last valid control value.
    try:
        set_shared(mode=read_integer("V5", 0, 1))
    except Exception:
        print("Cannot read V5 mode; keeping previous mode")
    try:
        set_shared(slider=read_integer("V3", 0, 180))
    except Exception:
        print("Cannot read V3 slider; keeping previous angle")

class IRSensor:
    """One event per debounced transition from clear to detected."""
    def __init__(self, pin_number):
        self.pin = machine.Pin(pin_number, machine.Pin.IN)
        self.stable = 1 - IR_ACTIVE_LEVEL
        self.candidate = self.pin.value()
        self.changed_at = time.ticks_ms()

    def poll(self, now):
        raw = self.pin.value()
        if raw != self.candidate:
            self.candidate = raw
            self.changed_at = now
        changed = False
        if (self.candidate != self.stable and
                time.ticks_diff(now, self.changed_at) >= DEBOUNCE_MS):
            self.stable = self.candidate
            changed = True
        detected = self.stable == IR_ACTIVE_LEVEL
        return changed, detected

class Gate:
    def __init__(self):
        self.pwm = machine.PWM(machine.Pin(SERVO_PIN), freq=50)
        self.angle = None
        self.opened_at = None
        self.move(CLOSED_ANGLE)

    def move(self, angle):
        angle = max(0, min(180, int(angle)))
        if angle != self.angle:
            duty = int(DUTY_MIN + angle * (DUTY_MAX - DUTY_MIN) / 180)
            self.pwm.duty(duty)  # Same ESP32 PWM calibration as Task 2.
            self.angle = angle
            print("Servo angle:", angle)

    def open_for_detection(self, now):
        self.move(OPEN_ANGLE)
        self.opened_at = now

    def poll_close(self, now):
        if (self.opened_at is not None and
                time.ticks_diff(now, self.opened_at) >= OPEN_TIME_MS):
            self.move(CLOSED_ANGLE)
            self.opened_at = None

    def cancel_auto(self):
        self.opened_at = None

class TM1637:
    """Small, built-in driver for a standard four-digit TM1637 module."""
    DIGITS = (0x3F, 0x06, 0x5B, 0x4F, 0x66,
              0x6D, 0x7D, 0x07, 0x7F, 0x6F)

    def __init__(self, clk_pin, dio_pin, brightness=3):
        # OPEN_DRAIN releases each line when its value is 1.
        self.clk = machine.Pin(clk_pin, machine.Pin.OPEN_DRAIN,
                               machine.Pin.PULL_UP, value=1)
        self.dio = machine.Pin(dio_pin, machine.Pin.OPEN_DRAIN,
                               machine.Pin.PULL_UP, value=1)
        self.brightness = max(0, min(7, brightness))

    def _wait(self):
        time.sleep_us(10)

    def _start(self):
        self.dio.value(1)
        self.clk.value(1)
        self._wait()
        self.dio.value(0)
        self._wait()
        self.clk.value(0)

    def _stop(self):
        self.clk.value(0)
        self.dio.value(0)
        self._wait()
        self.clk.value(1)
        self._wait()
        self.dio.value(1)
        self._wait()

    def _write_byte(self, value):
        for _ in range(8):
            self.clk.value(0)
            self.dio.value(value & 1)
            self._wait()
            self.clk.value(1)
            self._wait()
            value >>= 1
        self.clk.value(0)
        self.dio.value(1)  # Release DIO for the display's ACK.
        self._wait()
        self.clk.value(1)
        self._wait()
        acknowledged = self.dio.value() == 0
        self.clk.value(0)
        self._wait()
        return acknowledged

    def _transaction(self, values):
        self._start()
        try:
            for value in values:
                if not self._write_byte(value):
                    raise OSError("TM1637 did not acknowledge; check wiring/power")
        finally:
            self._stop()

    def number(self, value):
        text = "%4d" % (value % 10000)
        segments = [0 if ch == " " else self.DIGITS[int(ch)] for ch in text]
        self._transaction([0x40])  # Write data, automatic address increment.
        self._transaction([0xC0] + segments)
        self._transaction([0x88 | self.brightness])


def show_count(display, count):
    try:
        display.number(count)
    except OSError as error:
        # A disconnected display must not stop the sensor/gate loop.
        print(error)

# Only this background thread performs Wi-Fi/Blynk operations.
# The foreground loop owns the sensor, TM1637 and servo.
shared_lock = _thread.allocate_lock()
shared = {"status": "Not Detected", "count": 0,
          "angle": 0, "mode": 1, "slider": 90, "running": True}


def set_shared(**values):
    shared_lock.acquire()
    try:
        shared.update(values)
    finally:
        shared_lock.release()


def snapshot():
    shared_lock.acquire()
    try:
        return shared.copy()
    finally:
        shared_lock.release()


def api_get(query):
    response = None
    try:
        url = BLYNK_API + query
        try:
            response = requests.get(url, timeout=5)
        except TypeError:
            # Older urequests versions do not support the timeout keyword.
            response = requests.get(url)
        if response.status_code != 200:
            raise OSError("Blynk HTTP status %s" % response.status_code)
        return response.text
    finally:
        if response is not None:
            response.close()


def read_integer(pin, minimum, maximum):
    value = json.loads(api_get("/get?token=" + BLYNK_TOKEN + "&" + pin))
    if isinstance(value, list):
        if len(value) != 1:
            raise ValueError("Unexpected value for " + pin)
        value = value[0]
    number = float(value)
    integer = int(number)
    if number != integer or not minimum <= integer <= maximum:
        raise ValueError("Out-of-range value for " + pin)
    return integer


def write_value(pin, value):
    # Our outgoing values contain only letters, spaces and integer digits.
    encoded = str(value).replace(" ", "%20")
    api_get("/update?token=" + BLYNK_TOKEN + "&" + pin + "=" + encoded)


def connect_wifi(wifi):
    if wifi.isconnected():
        return True
    print("Connecting to Wi-Fi...")
    try:
        wifi.disconnect()
    except OSError:
        pass
    wifi.connect(WIFI_SSID, WIFI_PASS)
    started = time.ticks_ms()
    while not wifi.isconnected():
        if not snapshot()["running"]:
            return False
        if time.ticks_diff(time.ticks_ms(), started) >= 20000:
            print("Wi-Fi connection timed out; retrying later")
            return False
        time.sleep_ms(250)
    print("Wi-Fi connected")
    return True


def cloud_worker():
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    sent = {}
    last_refresh = time.ticks_ms()
    while snapshot()["running"]:
        try:
            if not connect_wifi(wifi):
                time.sleep_ms(3000)
                continue
            poll_controls()
            current = snapshot()
            now = time.ticks_ms()
            if time.ticks_diff(now, last_refresh) >= RESEND_MS:
                sent.clear()
                last_refresh = now
            for pin, key in TELEMETRY:
                value = current[key]
                if sent.get(pin) != value:
                    # Update the cache only after Blynk acknowledges success.
                    write_value(pin, value)
                    sent[pin] = value
        except Exception:
            # Avoid printing URLs/errors that could expose the auth token.
            print("Cloud update failed; check Wi-Fi, server, token and datastreams")
            time.sleep_ms(2000)
        time.sleep_ms(CLOUD_POLL_MS)


def main():
    sensor = IRSensor(IR_PIN)
    gate = Gate()
    display = TM1637(TM_CLK_PIN, TM_DIO_PIN, TM_BRIGHTNESS)
    count = 0
    mode = 1
    show_count(display, count)
    set_shared(status="Not Detected", count=count, angle=gate.angle,
               mode=mode, slider=90, running=True)
    _thread.start_new_thread(cloud_worker, ())
    print("Task 5: smart gate running; boot mode = Automatic")
    try:
        while True:
            now = time.ticks_ms()
            changed, detected = sensor.poll(now)
            controls = snapshot()
            requested_mode = controls["mode"]
            if requested_mode != mode:
                mode = requested_mode
                gate.cancel_auto()
                if mode == 1:
                    gate.move(CLOSED_ANGLE)
                    # An object already present is not a new detection.
                    print("Automatic mode: waiting for a new detection")
                else:
                    print("Manual mode: slider controls the servo")

            if changed:
                if detected:
                    count = (count + 1) % COUNTER_MODULUS
                    show_count(display, count)
                    print("Detection count:", count)
                    if mode == 1:
                        gate.open_for_detection(now)
                set_shared(status="Detected" if detected else "Not Detected",
                           count=count)

            if mode == 1:
                gate.poll_close(now)
            else:
                gate.move(controls["slider"])
            set_shared(angle=gate.angle)
            time.sleep_ms(10)
    finally:
        set_shared(running=False)
        gate.move(CLOSED_ANGLE)
        gate.pwm.deinit()


if __name__ == "__main__":
    main()
