# Arduino PC Controller

A minimal project to control an Arduino Uno/Nano from a PC over serial.  
A Python GUI (CustomTkinter) lets you adjust LED brightness via PWM and send a digital pulse — no Serial Monitor or code changes needed.

---

## Hardware Required

| Component | Notes |
|---|---|
| Arduino Uno or Nano | Tested on Uno R3 |
| LED + 220 Ω resistor | Connected to pin 11 (hardware PWM) |
| USB cable | Data cable — used for both power and serial |

> **Pin 13** is the Arduino onboard LED — no external component needed for the pulse.  
> **Pin 11** is used for PWM because pin A0 (physical pin 14) does not support hardware PWM on Arduino Uno.

---

## Wiring

```
Arduino Uno          Breadboard
───────────          ──────────
Pin 11  ──────────►  LED anode (+)
GND     ──────────►  LED cathode (–) via 220 Ω resistor

Pin 13  (onboard LED — no external wiring required)
```

| Arduino Pin | Direction | Component |
|---|---|---|
| 11 | OUTPUT PWM | External LED (anode via 220 Ω) |
| 13 | OUTPUT digital | Onboard LED (500 ms pulse) |
| GND | — | LED cathode / common ground |

---

## Installation

### 1. Firmware — Arduino IDE

1. Open **Arduino IDE** (1.x or 2.x).
2. Go to **File → Open** and select `firmware.ino`.
3. Select the board: **Tools → Board → Arduino Uno** (or Nano).
4. Select the port: **Tools → Port → COMx** (Windows) or `/dev/ttyUSBx` (Linux/Mac).
5. Click **Upload** (→ arrow).
6. Open the **Serial Monitor** at 9600 baud and confirm `READY` appears on boot.

### 2. Python Software

Requires Python 3.10 or later.

```bash
# Clone the repo (or download the ZIP)
git clone https://github.com/proxjack/test-board.git
cd test-board

# (Optional but recommended) virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch the controller
python controller.py
```

---

## Usage

1. Plug Arduino into the PC via USB.
2. Run `python controller.py`.
3. Select the serial port from the **Port** dropdown (e.g. `COM3` on Windows, `/dev/ttyUSB0` on Linux).
4. Click **Connect** — the app waits 2 seconds for the Arduino auto-reset, then shows `● Connected`.
5. Drag the **slider** (0–255) to adjust LED brightness on pin 11.
6. Click **500 ms Pulse** to drive pin 13 HIGH for half a second (onboard LED blinks).
7. All TX/RX messages appear in the log console at the bottom with timestamps.
8. Click **Disconnect** (or close the window) to release the serial port cleanly.

---

## Serial Protocol

**Settings:** 9600 baud, 8N1, newline `\n` terminator

### Commands (PC → Arduino)

| Command | Description | Example |
|---|---|---|
| `PWM:<value>` | Set LED brightness (0–255). Value is clamped automatically. | `PWM:128` |
| `PULSE` | Drive pin 13 HIGH for 500 ms, then LOW. Non-blocking. | `PULSE` |
| `PING` | Check connection | `PING` |

### Responses (Arduino → PC)

| Response | When sent |
|---|---|
| `READY` | On firmware boot |
| `PONG` | In reply to `PING` |
| `OK:PWM:<n>` | Confirms PWM value applied |
| `OK:PULSE` | Confirms pulse started |
| `ERR:UNKNOWN:<cmd>` | Unrecognised command |

---

## Project Structure

```
test-board/
├── firmware.ino       # Arduino sketch — non-blocking loop with millis()
├── controller.py      # Python GUI — CustomTkinter + pyserial, RX thread
├── requirements.txt   # Python dependencies
├── .gitignore         # Standard Python ignores
└── README.md          # This file
```

---

## Troubleshooting

### Serial port not visible in the dropdown
- Make sure you are using a **data** USB cable, not a charge-only cable.
- Click **↻** to refresh the port list.
- On Windows: check **Device Manager → Ports (COM & LPT)** for `Arduino Uno (COMx)`.
- If you use a Nano clone with a CH340/CH341 chip, install the matching USB-serial driver.

### Permission error on Linux (`Permission denied: /dev/ttyUSB0`)
Add your user to the `dialout` group and log out/in:
```bash
sudo usermod -aG dialout $USER
# then log out and back in, or run:
newgrp dialout
```

### Arduino does not respond after connecting
- The app automatically waits 2 seconds for the reset — wait until the status shows `● Connected`.
- If the issue persists, press the physical **RESET** button on Arduino while the port is open.
- Make sure no other program (Arduino IDE Serial Monitor, etc.) is using the same port.

### LED does not light up
- Check LED polarity: anode to pin 11, cathode to GND via resistor.
- Verify the resistor is ~220 Ω (color bands: red-red-brown).
- Send `PING` — if you get `PONG` back, the firmware is working and the issue is in the circuit.
