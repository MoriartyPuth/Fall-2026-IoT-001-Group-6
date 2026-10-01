# Lab 3: IoT Smart Gate Control with Blynk, IR Sensor, Servo Motor, and TM1637

## Equiment
- ESP32 development board (MicroPython firmware flashed)
- IR obstacle detection sensor
- SG90 servo motor
- TM1637 4-digit 7-segment display
- Breadboard and jumper wires
- USB cable and laptop with Thonny
- Wi-Fi access and Blynk account

## Wiring
<img width="1151" height="639" alt="image" src="https://github.com/user-attachments/assets/bcab0153-6d66-459b-bffd-ffc18cb15bcd" />

## Task 1 : IR Sensor Monitoring
- Read the digital output of the IR sensor using the ESP32.
- Display the sensor status (Detected / Not Detected) on Blynk.
- Update the status whenever the sensor state changes.

### Evidence
<img width="1280" height="743" alt="image" src="https://github.com/user-attachments/assets/bcb748b0-2005-42e2-ab3c-268b93ce7bb4" />
<img width="1280" height="743" alt="image" src="https://github.com/user-attachments/assets/56394891-db7f-4940-b7ed-381931b1fe20" />

## Task 2 : Blynk-Controlled Servo
- Add a Blynk slider with a range from 0 to 180 degrees.
- Moving the slider must change the servo angle.
- Display the selected angle in the Blynk app.

### [Evidence](https://drive.google.com/file/d/1c1Wx28Jv6XwF2s1hnTsWy2VEQmLn2xPO/view?usp=sharing)

## Task 3 : Automatic IR Gate Operation
- When an object is detected by the IR sensor, the servo must open the gate.
- After a short delay, the servo returns to the closed position.
- Trigger each opening once per new detection, not repeatedly while an object remains present.

### [Evidence](https://drive.google.com/file/d/1cuRAaU5BvuY10YOzahROenOFIo-DNKQO/view?usp=sharing) 

## Task 4 : TM1637 Detection Counter
- Count each new IR detection event.
- Display the count on the TM1637 display.
- Send the same count to a Blynk numeric display widget.

### [Evidence](https://drive.google.com/file/d/1fiZfzvEib69NOkhfyYiUQ9rAc8yn10Sf/view?usp=sharing)

## Task 5 : Complete Smart Gate Integration
- Combine all previous tasks into one ESP32 program and one Blynk dashboard.
- Add a switch in Blynk to select Automatic or Manual mode.
- In Automatic mode, the IR sensor controls the gate. In Manual mode, the IR sensor does not
move the servo; use the Blynk slider instead.
- Keep the IR status and detection counter visible on Blynk.

### [Evidence](https://drive.google.com/file/d/1FsLOEQMsLBq2-ibRB9NIJdVcPi03uJv4/view?usp=sharing)

## Wi-Fi and Blynk Setup

1. Set `WIFI_SSID`, `WIFI_PASS`, and `BLYNK_TOKEN` in the code.
2. Connect the ESP32 to a 2.4 GHz Wi-Fi network.
3. Use the token from your Blynk device.
4. Create these datastreams and widgets on one dashboard:

| Virtual Pin | Data Type | Widget | Function |
|-------------|-----------|--------|----------|
| V2 | String | Value Display | Shows Detected / Not Detected |
| V3 | Integer, 0–180 | Slider | Selects the manual servo angle |
| V4 | Integer, 0–9999 | Numeric Display | Shows the detection count |
| V5 | Integer, 0–1 | Switch | Selects Automatic or Manual mode |
| V6 | Integer, 0–180 | Numeric Display | Shows the commanded servo angle |

## Using the Blynk Controls

- **Mode switch (V5):** ON = Automatic; OFF = Manual.
- **Servo slider (V3):** In Manual mode, move the slider to set the servo angle.
- **Automatic mode:** A new IR detection opens the gate, which closes after two seconds.
- **IR status (V2):** Shows whether an object is detected.
- **Detection counter (V4):** Shows the same count as the TM1637.
- **Servo angle (V6):** Shows the angle commanded by the ESP32.

IR status and detection counting remain active in both modes.
