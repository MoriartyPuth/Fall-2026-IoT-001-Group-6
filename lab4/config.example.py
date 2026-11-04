# Copy to config.py and fill in before uploading to the ESP32

WIFI_SSID = "YOUR_WIFI_NAME"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# The computer running Node-RED (find it with: ipconfig getifaddr en0)
NODE_RED_URL = "http://YOUR_PC_IP:1880/lab4/data"

DEVICE_ID = "esp32-lab4"
SEND_INTERVAL_MS = 2000

# Local timezone written to the DS3231 when it is synced from NTP (Cambodia = UTC+7)
TZ_OFFSET_HOURS = 7
# Set the DS3231 from internet time at boot (only when WiFi is up)
SYNC_RTC_FROM_NTP = True

# Sea-level pressure used for the altitude estimate
SEA_LEVEL_HPA = 1013.25
