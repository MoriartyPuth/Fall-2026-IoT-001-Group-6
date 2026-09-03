import dht
import gc
from machine import Pin
import network
import time
import ujson
import urequests

# ==========================================
# 1. CONFIGURATION (WIFI & TELEGRAM)
# ==========================================
SSID = "Robotic WIFI"
PASSWORD = "rbtWIFI@2025"

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = ""

URL_SEND = "https://api.telegram.org/bot{}/sendMessage".format(BOT_TOKEN)
URL_UPDATES = "https://api.telegram.org/bot{}/getUpdates".format(BOT_TOKEN)

# ==========================================
# 2. HARDWARE SETUP
# ==========================================
sensor = dht.DHT11(Pin(33))

# Relay / LED Pin (Pin 2 is onboard LED; change to your relay pin if different)
relay = Pin(2, Pin.OUT)
relay.value(0)  # Start with relay OFF

# State variables
relay_is_on = False  # Track if relay is ON or OFF
TEMP_THRESHOLD = 27  # °C threshold

# ==========================================
# 3. WIFI CONNECTION
# ==========================================
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)

print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)

print("WiFi connected successfully!")

# ==========================================
# 4. SAFE TELEGRAM SEND FUNCTION
# ==========================================
def send_telegram(text):
    """Sends message encoded in UTF-8 bytes to avoid error 400 & socket leaks."""
    headers = {"Content-Type": "application/json"}
    payload = {"chat_id": CHAT_ID, "text": text}
    body = ujson.dumps(payload).encode('utf-8')
    
    try:
        res = urequests.post(URL_SEND, data=body, headers=headers)
        res.close()
    except Exception as e:
        print("Error sending message:", e)

# ==========================================
# 5. MAIN LOOP (TASK 4 LOGIC)
# ==========================================
last_update_id = 0
last_alert_time = time.ticks_ms()

print("Task 4 Bot is running...")

while True:
    gc.collect()

    # ----------------------------------------------------
    # STEP A: Check for /on command from Telegram
    # ----------------------------------------------------
    try:
        url = "{}?offset={}&timeout=1".format(URL_UPDATES, last_update_id + 1)
        res = urequests.get(url)
        data = res.json()
        res.close()

        for update in data.get("result", []):
            last_update_id = update["update_id"]

            message_data = update.get("message", {})
            text = message_data.get("text", "").strip()

            command = text.split()[0].lower() if text else ""
            command_name = command.split("@")[0]

            # When /on is received: Turn relay ON and stop alerts
            if command_name == "/on":
                relay.value(1)
                relay_is_on = True
                print("Received /on -> Relay is now ON. Alerts stopped.")
                send_telegram("Relay turned ON. Temperature alerts stopped.")

            # Optional helper to check current temperature anytime
            elif command_name == "/temp":
                try:
                    sensor.measure()
                    t = sensor.temperature()
                    h = sensor.humidity()
                    send_telegram("Current Temp: {} °C | Humidity: {} %".format(t, h))
                except:
                    pass

    except Exception as e:
        print("Polling error:", e)

    # ----------------------------------------------------
    # STEP B: Measure Temperature & Apply Rules Every 5s
    # ----------------------------------------------------
    if time.ticks_diff(time.ticks_ms(), last_alert_time) >= 5000:
        last_alert_time = time.ticks_ms()

        try:
            sensor.measure()
            temp = sensor.temperature()
            print("Check (every 5s) -> Temp: {} °C | Relay ON: {}".format(temp, relay_is_on))

            # RULE 1: If T >= 27 °C and relay is OFF -> Send alert every 5 seconds until /on
            if temp >= TEMP_THRESHOLD and not relay_is_on:
                alert_msg = "ALERT: Temperature is {} °C (>= 27 °C)! Relay is OFF. Send /on to turn it ON.".format(temp)
                print("Sending 5s alert...")
                send_telegram(alert_msg)

            # RULE 2: After /on, when T < 27 °C -> Turn relay OFF and send ONE-TIME notice
            elif temp < TEMP_THRESHOLD and relay_is_on:
                relay.value(0)  # Turn relay OFF
                relay_is_on = False  # Switch state back to OFF
                auto_off_msg = "Auto-OFF: Temperature dropped to {} °C (< 27 °C). Relay has been turned OFF automatically.".format(temp)
                print("Sending one-time auto-OFF notice...")
                send_telegram(auto_off_msg)

            # RULE 3: While T < 27 °C and relay is OFF -> No messages are sent
            elif temp < TEMP_THRESHOLD and not relay_is_on:
                pass  # Completely silent

        except Exception as e:
            print("Sensor read error:", e)

    time.sleep(0.5)
