# LAB1: Temperature Sensor with Relay Control (Telegram)

## Group Information

- **Course:** Introduction to Internet of Things
- **Lab:** LAB1 – Temperature Sensor with Relay Control (Telegram)
- **Group:** Group 6

## Project Overview

This project uses an ESP32, DHT11 temperature and humidity sensor, relay module, Wi-Fi, and Telegram Bot API. The ESP32 reads the sensor every five seconds, allows users to check the system and control the relay through Telegram commands, sends repeated high-temperature alerts, and turns the relay off automatically after the temperature becomes safe.

## Equipment

- ESP32 development board with MicroPython
- DHT11 sensor
- Relay module (or onboard LED indicator)
- Jumper wires
- USB cable and laptop with Thonny
- Wi-Fi connection
- Telegram bot and group

## Wiring

| Component | Component pin | ESP32 connection |
|---|---|---|
| DHT11 | VCC | 5V / 3.3V |
| DHT11 | DATA | GPIO 33 |
| DHT11 | GND | GND |
| Relay | VCC | 5V / 3.3V |
| Relay | IN | GPIO 2 |
| Relay | GND | GND |

### Wiring Diagram

<img width="1732" height="982" alt="image" src="https://github.com/user-attachments/assets/bac46ea9-7459-4aee-b519-bf22a93794e9" />

---

## Task 1 — Sensor Read and Print (10 points)

### Requirement

Read the DHT11 temperature and humidity every five seconds and print both values with formatting in the Thonny Shell.

### Task 1 Evidence

<img width="327" height="184" alt="image" src="https://github.com/user-attachments/assets/224e5608-b101-435e-80d1-12b6f956cdb3" />


---

## Task 2 — Telegram Send (15 points)

### Requirement

Implement the `send_telegram()` function and use the ESP32 to send a message to the Telegram group.

### Task 2 Evidence

---

## Task 3 — Telegram Bot Commands (15 points)

### Requirement

The Telegram bot supports commands from the group:

- `/temp` — replies with the current temperature and humidity.
- `/on` — turns the relay ON.
- `/off` — turns the relay OFF.

### Task 3 Evidence

<img width="627" height="543" alt="image" src="https://github.com/user-attachments/assets/42cc35eb-e606-4709-9a5a-ec0051918b03" />


---

## Task 4 — Automatic Temperature and Relay Control (30 points)

### Requirement

- When the temperature is below 27°C, the system sends no automatic alert.
- When the temperature is 27°C or higher and the relay is OFF, the bot sends an alert every five seconds.
- Alerts continue until the `/on` command is received.
- After `/on`, the relay turns ON and the repeated alerts stop.
- When the temperature drops below 27°C, the relay turns OFF automatically.
- The bot sends one automatic OFF notification.

### Task 4 High-Temperature Evidence

<img width="1106" height="698" alt="image" src="https://github.com/user-attachments/assets/695922a6-831f-4632-be9c-5c360c3cffe5" />


### Task 4 Demonstration Video

---

## Task 5 — Documentation (30 points)

This diagram illustrates the state machine and loop logic used in the firmware.

<img width="805" height="631" alt="image" src="https://github.com/user-attachments/assets/ac089c9b-7403-4f13-8a51-08bf3bc5d8b7" />


### Telegram Usage

| Command | Function |
|---|---|
| `/temp` | Show current temperature and humidity |
| `/on` | Turn the relay ON and stop high-temperature alerts |

---
