# TestBoard PC Controller

A minimal project to control the **TestBoard** — a custom board built around an ATmega328P running the Arduino bootloader — from a PC over serial.  
A Python GUI (CustomTkinter) lets you toggle an LED on/off and send a digital pulse, with a live serial log.

---

## Hardware Required

| Component | Notes |
|---|---|
| TestBoard | ATmega328P + Arduino bootloader |
| LED + 220 Ω resistor | Connected to pin 14 |
| USB cable | Data cable — used for both power and serial |

> **Pin 13** drives the onboard LED — no external component needed for the pulse.

---

## Wiring

```
TestBoard            Breadboard
─────────            ──────────
Pin 14  ──────────►  LED anode (+)
GND     ──────────►  LED cathode (–) via 220 Ω resistor

Pin 13  (onboard LED — no external wiring required)
```

| TestBoard Pin | Direction | Component |
|---|---|---|
| 11 | OUTPUT digital | External LED (anode via 220 Ω) |
| 13 | OUTPUT digital | Onboard LED (500 ms pulse) |
| GND | — | LED cathode / common ground |

---

## Installation

### 1. Firmware — Arduino IDE

1. Open **Arduino IDE** (1.x or 2.x).
2. Go to **File → Open** and select `Software/firmware.ino`.
3. Select the board: **Tools → Board → Arduino Uno** (ATmega328P, same bootloader).
4. Select the port: **Tools → Port → COMx** (Windows) or `/dev/ttyUSBx` (Linux/Mac).
5. Click **Upload** (→ arrow).
6. Open the **Serial Monitor** at 9600 baud and confirm `READY` appears on boot.

### 2. Python Software

Requires Python 3.10 or later.

```bash
# Clone the repo (or download the ZIP)
git clone https://github.com/proxjack/TestBoard.git
cd TestBoard

# (Optional but recommended) virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch the controller
python Software/controller.py
```

---

## Usage

1. Plug the TestBoard into the PC via USB.
2. Run `python Software/controller.py`.
3. Select the serial port from the **Port** dropdown (e.g. `COM3` on Windows, `/dev/ttyUSB0` on Linux).
4. Click **Connect** — the app waits 2 seconds for the board auto-reset, then shows `● Connected`.
5. Click **LED OFF / LED ON** to toggle the LED on pin 14.
6. Click **500 ms Pulse** to drive pin 13 HIGH for half a second (onboard LED blinks).
7. All TX/RX messages appear in the serial log at the bottom with timestamps.
8. Click **Disconnect** (or close the window) to release the serial port cleanly.

---

## Serial Protocol

**Settings:** 9600 baud, 8N1, newline `\n` terminator

### Commands (PC → TestBoard)

| Command | Description |
|---|---|
| `LED:ON` | Turn LED on (pin 14 HIGH) |
| `LED:OFF` | Turn LED off (pin 14 LOW) |
| `PULSE` | Drive pin 13 HIGH for 500 ms, then LOW. Non-blocking. |
| `PING` | Check connection |

### Responses (TestBoard → PC)

| Response | When sent |
|---|---|
| `READY` | On firmware boot |
| `PONG` | In reply to `PING` |
| `OK:LED:ON` | Confirms LED turned on |
| `OK:LED:OFF` | Confirms LED turned off |
| `OK:PULSE` | Confirms pulse started |
| `ERR:UNKNOWN:<cmd>` | Unrecognised command |

---

## Project Structure

```
TestBoard/
├── Software/
│   ├── firmware.ino   # TestBoard sketch — non-blocking loop with millis()
│   └── controller.py  # Python GUI — CustomTkinter + pyserial, RX thread
├── requirements.txt   # Python dependencies
├── .gitignore         # Standard Python ignores
└── README.md          # This file
```

---

## Troubleshooting

### Serial port not visible in the dropdown
- Make sure you are using a **data** USB cable, not a charge-only cable.
- Click **↻** to refresh the port list.
- On Windows: check **Device Manager → Ports (COM & LPT)** for the TestBoard entry.
- If the board uses a CH340/CH341 USB-serial chip, install the matching driver.

### Permission error on Linux (`Permission denied: /dev/ttyUSB0`)
Add your user to the `dialout` group and log out/in:
```bash
sudo usermod -aG dialout $USER
# then log out and back in, or run:
newgrp dialout
```

### Board does not respond after connecting
- The app automatically waits 2 seconds for the reset — wait until the status shows `● Connected`.
- If the issue persists, press the physical **RESET** button on the board while the port is open.
- Make sure no other program (Arduino IDE Serial Monitor, etc.) is using the same port.

### LED does not light up
- Check LED polarity: anode to pin 14, cathode to GND via resistor.
- Verify the resistor is ~220 Ω (color bands: red-red-brown).
- Send `PING` — if you get `PONG` back, the firmware is working and the issue is in the circuit.
