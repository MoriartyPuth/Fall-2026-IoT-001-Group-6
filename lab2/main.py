# ============================================================
# COMBINED MAIN.PY
# Task 1 & 2 : DHT11 + HC-SR04 sensors, LCD Show/Hide buttons
# Task 3      : Web-controlled SG90 servo (slider, 0-180 degrees)
# Task 4      : Custom text-to-LCD (textbox + scrolling messages)
# ============================================================

# ---------------- Import the library ----------------
import network
import socket
import time
import dht

from machine import Pin, time_pulse_us, SoftI2C, PWM
from machine_i2c_lcd import I2cLcd

# ---------------- WIFI Setup ----------------
ssid = "Robotic WIFI"
password = "rbtWIFI@2025"

# ---------------- Sensor Pin Setup ----------------
# DHT11 data pin
dht_sensor = dht.DHT11(Pin(4))

# HC-SR04 pins
trig = Pin(27, Pin.OUT)
echo = Pin(26, Pin.IN)

# ---------------- Servo Setup ----------------
servo = PWM(Pin(13), freq=50)
servo_angle = 90  # start centred at 90 degrees

# ---------------- LCD SETUP ----------------
I2C_ADDR = 0x27

i2c = SoftI2C(
    sda=Pin(21),
    scl=Pin(22),
    freq=400000
)

lcd = I2cLcd(
    i2c,
    I2C_ADDR,
    2,
    16
)

lcd.clear()

### Display the text -> IoT Class on the first row
lcd.move_to(0, 0)
lcd.putstr("IoT Class")

### Display the text -> Lab 2 & Task 4 on the second Row
lcd.move_to(0, 1)
lcd.putstr("Lab 2 & Task 4")

# ---------------- Set the Show state to False ----------------
show_distance = False
show_temperature = False


# ============================================================
# Read distance from the ultrasonic sensor (HC-SR04)
# ============================================================
def read_distance():
    try:
        # set Trigger to off for 2us
        trig.value(0)
        time.sleep_us(1)

        # set Trigger to on for 10us
        trig.value(1)
        time.sleep_us(10)

        # set Trigger to off again
        trig.value(0)

        # Measure the ECHO pulse
        duration = time_pulse_us(echo, 1, 30000)

        # make a condition if the duration less than 0 return None
        if duration < 0:
            return None

        # Convert time to distance in centimetres with the formula d = v*t/2
        distance = (duration * 0.0343) / 2

        return distance

    except Exception as error:
        print("Ultrasonic error:", error)
        return None


# ============================================================
# Read temperature and humidity from the DHT11
# ============================================================
def read_dht11():
    try:
        dht_sensor.measure()

        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()

        return temperature, humidity

    except Exception as error:
        print("DHT11 error:", error)
        return None, None


# ============================================================
# TASK 3: Move the SG90 servo to the given angle (0-180)
# ============================================================
def move_servo(angle):
    # Keep the angle between 0 and 180 degrees
    if angle < 0:
        angle = 0

    if angle > 180:
        angle = 180

    # Servo PWM duty range
    duty_min = 26
    duty_max = 128

    # Convert angle 0-180 degrees to servo duty
    duty = int(
        duty_min
        + (angle / 180)
        * (duty_max - duty_min)
    )

    # Send the calculated duty to the servo
    servo.duty(duty)

    print("Servo angle:", angle)
    print("PWM duty:", duty)


# ============================================================
# Clear a single ROW on the LCD
# ============================================================
def clear_lcd_row(row):
    lcd.move_to(0, row)
    # 16 spaces clear the entire row
    lcd.putstr("                ")


# ============================================================
# Display the Distance on Row 0
# ============================================================
def display_distance(distance):
    clear_lcd_row(0)
    lcd.move_to(0, 0)
    if distance is None:
        lcd.putstr("Distance Error")
    else:
        lcd.putstr("Dist: {:.1f} cm".format(distance))


# ============================================================
# Display the Temperature on Row 1
# ============================================================
def display_temperature(temperature):
    clear_lcd_row(1)
    lcd.move_to(0, 1)
    if temperature is None:
        lcd.putstr("Temp Error")
    else:
        lcd.putstr("Temp: {} C".format(temperature))


# ============================================================
# TASK 4: Decode a URL-encoded (percent / +) string
# ============================================================
def url_decode(text):

    result = bytearray()
    index = 0

    while index < len(text):

        if text[index] == "+":
            # Convert + to a space
            result.append(32)
            index += 1

        elif text[index] == "%":
            try:
                hex_value = text[index + 1:index + 3]
                result.append(int(hex_value, 16))
                index += 3

            except Exception as error:
                # Malformed %xx sequence - keep the raw character
                result.append(ord(text[index]))
                index += 1

        else:
            result.append(ord(text[index]))
            index += 1

    return result.decode()


# ============================================================
# TASK 4: Display a custom message on the LCD (scrolls if >16 chars)
# After showing the message, redraw distance/temperature rows
# if they were being shown, so Task 1/2 state is not lost.
# ============================================================
def display_message(message):
    lcd.clear()

    if len(message) <= 16:
        lcd.putstr(message)
    else:
        lcd.scroll_text(message)

    if show_distance:
        display_distance(last_distance)
    if show_temperature:
        display_temperature(last_temperature)


# ============================================================
# Build the combined webpage (sensors + LCD controls + text box)
# ============================================================
def create_webpage(
    temperature,
    humidity,
    distance,
    show_distance,
    show_temperature,
    servo_angle
):

    if temperature is None:
        temperature_text = "Sensor error"
    else:
        temperature_text = str(temperature) + " &deg;C"

    if humidity is None:
        humidity_text = "Sensor error"
    else:
        humidity_text = str(humidity) + " %"

    if distance is None:
        distance_text = "Out of range"
    else:
        distance_text = "{:.1f} cm".format(distance)

    distance_btn_text = "Hide Distance" if show_distance else "Show Distance"
    temperature_btn_text = "Hide Temperature" if show_temperature else "Show Temperature"

    html = """<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Sensor Monitoring</title>
    <meta name="viewport"
        content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
            text-align: center;
            margin: 0;
            padding: 20px;
        }
        h1 {
            color: #333;
        }
        .container {
            max-width: 320px;
            margin: 0 auto;
        }
        .card {
            background-color: #ffffff;
            border-radius: 10px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
            padding: 20px;
            margin-bottom: 20px;
        }
        .card h2 {
            margin-top: 0;
            font-size: 18px;
            color: #222;
        }
        .label {
            font-size: 14px;
            color: #555;
            margin-top: 10px;
        }
        .value {
            font-size: 28px;
            font-weight: bold;
            color: #1e6fd9;
            margin: 5px 0 10px 0;
        }
        input[type=text] {
            width: 100%;
            padding: 10px;
            margin: 12px 0;
            border: 1px solid #ccc;
            border-radius: 6px;
            font-size: 14px;
            box-sizing: border-box;
        }
        input[type=range] {
            width: 100%;
            margin: 15px 0;
        }
        .hint {
            font-size: 13px;
            color: #777777;
            margin-top: 10px;
        }
        .btn, button {
            display: block;
            width: 100%;
            background-color: #1e6fd9;
            color: #ffffff;
            border: none;
            padding: 12px;
            margin: 8px 0;
            border-radius: 6px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            text-decoration: none;
            box-sizing: border-box;
        }
        .btn:active, button:active {
            opacity: 0.85;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>ESP32 Sensor Monitoring</h1>
        <div class="card">
            <h2>DHT11 Sensor</h2>
            <div class="label">Temperature</div>
            <div class="value">""" + temperature_text + """</div>
            <div class="label">Humidity</div>
            <div class="value">""" + humidity_text + """</div>
        </div>
        <div class="card">
            <h2>HC-SR04 Sensor</h2>
            <div class="label">Distance</div>
            <div class="value">""" + distance_text + """</div>
        </div>
        <div class="card">
            <h2>LCD Control</h2>
            <a class="btn" href="/?distance=toggle">""" + distance_btn_text + """</a>
            <a class="btn" href="/?temperature=toggle">""" + temperature_btn_text + """</a>
        </div>
        <div class="card">
            <h2>Servo Angle</h2>
            <div class="value" id="angleValue">""" + str(servo_angle) + """ degrees</div>
            <input type="range" min="0" max="180" value=\"""" + str(servo_angle) + """\"
                oninput="document.getElementById('angleValue').innerText = this.value + ' degrees'"
                onchange="location.href='/?angle=' + this.value">
            <div class="hint">Move the slider to control the servo.</div>
        </div>
        <div class="card">
            <h2>Send Text to LCD</h2>
            <form action="/" method="GET">
                <input type="text" name="message" placeholder="Enter your message">
                <button type="submit">Send</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

    return html


# ============================================================
# Connect to WIFI
# ============================================================
wifi = network.WLAN(network.STA_IF)
wifi.active(True)

if not wifi.isconnected():
    print("Connecting to Wi-Fi...")
    wifi.connect(ssid, password)

    while not wifi.isconnected():
        print(".", end="")
        time.sleep(1)

ip = wifi.ifconfig()[0]

print()
print("Wi-Fi connected!")
print("ESP32 IP address:", ip)
print("Open this address in your browser:")
print("http://" + ip)

# ===========================
# START WEB SERVER
# ===========================

address = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(address)
server.listen(1)
print("Web server running on port 80")

# TASK 3: set the servo to its initial position
move_servo(servo_angle)

# Track last known sensor readings so display_message() can
# redraw the distance/temperature rows after showing a message
last_distance = None
last_temperature = None

# ============================================================
# Main Program
# ============================================================
while True:

    client = None

    try:
        client, client_address = server.accept()

        print("Browser connected:", client_address)

        # Receive and decode browser request
        request = client.recv(1024).decode()

        print("Request received")

        # Read sensors
        temperature, humidity = read_dht11()
        distance = read_distance()

        last_temperature = temperature
        last_distance = distance

        print("Temperature:", temperature)
        print("Humidity:", humidity)
        print("Distance:", distance)

        request_line = request.split("\r\n")[0]

        # TASK 2: DISTANCE BUTTON
        if "/?distance=toggle" in request_line:
            show_distance = not show_distance

            if show_distance:
                display_distance(distance)
            else:
                clear_lcd_row(0)

        # TASK 2: TEMPERATURE BUTTON
        if "/?temperature=toggle" in request_line:
            show_temperature = not show_temperature

            if show_temperature:
                display_temperature(temperature)
            else:
                clear_lcd_row(1)

        # TASK 3: SERVO SLIDER
        if "/?angle=" in request_line:
            try:
                angle_str = request_line.split("angle=")[1]
                angle_str = angle_str.split(" ")[0]
                angle_str = angle_str.split("&")[0]

                servo_angle = int(angle_str)
                move_servo(servo_angle)

            except Exception as error:
                print("Angle parse error:", error)

        # TASK 4: CUSTOM TEXT MESSAGE
        if "/?message=" in request_line:
            try:
                raw_message = request_line.split("message=")[1]
                raw_message = raw_message.split(" ")[0]

                decoded_message = url_decode(raw_message)
                print("Decoded message:", decoded_message)

                if decoded_message:
                    display_message(decoded_message)

            except Exception as error:
                print("Message decode error:", error)

        # Create webpage
        webpage = create_webpage(
            temperature,
            humidity,
            distance,
            show_distance,
            show_temperature,
            servo_angle
        )

        # Send HTTP response
        client.send("HTTP/1.1 200 OK\r\n")
        client.send("Content-Type: text/html\r\n")
        client.send("Connection: close\r\n\r\n")
        client.sendall(webpage)
        client.close()

    except Exception as error:
        print("Error:", error)
        if client:
            client.close()

    time.sleep(0.1)
