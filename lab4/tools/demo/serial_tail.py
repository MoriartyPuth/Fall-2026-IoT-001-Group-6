"""Print the ESP32 serial output line by line (used by record_demo.js)."""
import sys

import serial

port = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbserial-0001"
ser = serial.Serial()
ser.port = port
ser.baudrate = 115200
ser.timeout = 1
ser.dtr = False  # don't reset the board when the port opens
ser.rts = False
ser.open()
while True:
    line = ser.readline()
    if line:
        sys.stdout.write(line.decode("utf-8", "replace"))
        sys.stdout.flush()
