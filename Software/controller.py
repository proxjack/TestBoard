"""
TestBoard PC Controller — GUI with CustomTkinter + pyserial
Dependencies: pip install customtkinter pyserial
"""

import time
import queue
import threading
from datetime import datetime

from pathlib import Path
from PIL import Image
import tkinter as tk

import serial
import serial.tools.list_ports
import customtkinter as ctk

_LOGO_PATH = Path(__file__).parent / "Amperry_Logo.png"

BAUD_RATE     = 9600
POLL_INTERVAL = 50   # ms — how often the main thread drains the RX queue
RESET_DELAY   = 2.0  # seconds — wait for TestBoard auto-reset after port open


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("TestBoard PC Controller")
        self.resizable(False, False)

        if _LOGO_PATH.exists():
            self._tk_icon = tk.PhotoImage(file=str(_LOGO_PATH))
            self.iconphoto(True, self._tk_icon)

        self._serial: serial.Serial | None      = None
        self._rx_queue: queue.Queue[str]        = queue.Queue()
        self._rx_thread: threading.Thread | None = None
        self._led_on: bool                      = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_rx()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # Logo
        if _LOGO_PATH.exists():
            logo_img = ctk.CTkImage(
                light_image=Image.open(_LOGO_PATH),
                dark_image=Image.open(_LOGO_PATH),
                size=(180, 50)
            )
            ctk.CTkLabel(self, image=logo_img, text="").pack(pady=(12, 4))

        # Port row
        row_port = ctk.CTkFrame(self, fg_color="transparent")
        row_port.pack(fill="x", **pad)

        ctk.CTkLabel(row_port, text="Port:").pack(side="left")

        self._port_var = ctk.StringVar(value="")
        self._port_menu = ctk.CTkOptionMenu(
            row_port, variable=self._port_var,
            values=self._list_ports(), width=160
        )
        self._port_menu.pack(side="left", padx=(6, 0))

        ctk.CTkButton(
            row_port, text="↻", width=36,
            command=self._refresh_ports
        ).pack(side="left", padx=(4, 0))

        self._connect_btn = ctk.CTkButton(
            row_port, text="Connect", width=110,
            command=self._toggle_connection
        )
        self._connect_btn.pack(side="left", padx=(10, 0))

        # Connection status
        self._status_label = ctk.CTkLabel(
            self, text="● Disconnected",
            text_color="#e05555", font=ctk.CTkFont(size=13, weight="bold")
        )
        self._status_label.pack(**pad)

        ctk.CTkFrame(self, height=2, fg_color="#333").pack(fill="x", padx=12, pady=2)

        # LED toggle button
        self._led_btn = ctk.CTkButton(
            self, text="LED  OFF",
            width=200, height=40,
            fg_color="#444", hover_color="#555",
            command=self._toggle_led,
            state="disabled"
        )
        self._led_btn.pack(**pad)

        # Solenoid test button
        self._solenoid_btn = ctk.CTkButton(
            self, text="Solenoid Test (pin 13)",
            command=self._send_solenoid,
            state="disabled"
        )
        self._solenoid_btn.pack(**pad)

        ctk.CTkFrame(self, height=2, fg_color="#333").pack(fill="x", padx=12, pady=2)

        # Serial log
        ctk.CTkLabel(self, text="Serial log", font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=12, pady=(6, 0)
        )
        self._log = ctk.CTkTextbox(
            self, width=460, height=180,
            font=ctk.CTkFont(family="Courier New", size=11),
            state="disabled"
        )
        self._log.pack(padx=12, pady=(2, 12))

    # ------------------------------------------------------------------
    # Serial ports
    # ------------------------------------------------------------------
    def _list_ports(self) -> list[str]:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        return ports if ports else ["(no port)"]

    def _refresh_ports(self):
        ports = self._list_ports()
        self._port_menu.configure(values=ports)
        self._port_var.set(ports[0])

    # ------------------------------------------------------------------
    # Connect / disconnect
    # ------------------------------------------------------------------
    def _toggle_connection(self):
        if self._serial and self._serial.is_open:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self._port_var.get()
        if not port or port == "(no port)":
            self._log_line("SYS", "No port selected.")
            return
        try:
            self._serial = serial.Serial(port, BAUD_RATE, timeout=0.1)
        except serial.SerialException as exc:
            self._log_line("ERR", str(exc))
            return

        self._log_line("SYS", f"Port open: {port} — waiting for board reset…")
        threading.Thread(target=self._post_connect_init, daemon=True).start()

    def _post_connect_init(self):
        time.sleep(RESET_DELAY)
        if self._serial and self._serial.is_open:
            self._serial.reset_input_buffer()
        self.after(0, self._on_connected)

    def _on_connected(self):
        self._connect_btn.configure(text="Disconnect")
        self._status_label.configure(text="● Connected", text_color="#55e075")
        self._led_btn.configure(state="normal")
        self._solenoid_btn.configure(state="normal")
        self._log_line("SYS", "Ready.")
        self._rx_thread = threading.Thread(target=self._rx_worker, daemon=True)
        self._rx_thread.start()

    def _disconnect(self):
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

        self._led_on = False
        self._connect_btn.configure(text="Connect")
        self._status_label.configure(text="● Disconnected", text_color="#e05555")
        self._led_btn.configure(text="LED  OFF", fg_color="#444", state="disabled")
        self._solenoid_btn.configure(state="disabled")
        self._log_line("SYS", "Disconnected.")

    # ------------------------------------------------------------------
    # RX thread — pushes received lines into the queue
    # ------------------------------------------------------------------
    def _rx_worker(self):
        while self._serial and self._serial.is_open:
            try:
                line = self._serial.readline().decode("utf-8", errors="replace").strip()
                if line:
                    self._rx_queue.put(line)
            except serial.SerialException:
                self._rx_queue.put("__SERIAL_ERROR__")
                break

    # ------------------------------------------------------------------
    # Main-thread queue drain (runs every POLL_INTERVAL ms)
    # ------------------------------------------------------------------
    def _poll_rx(self):
        try:
            while True:
                line = self._rx_queue.get_nowait()
                if line == "__SERIAL_ERROR__":
                    self._log_line("ERR", "Serial error — disconnecting.")
                    self._disconnect()
                else:
                    self._log_line("RX", line)
        except queue.Empty:
            pass
        self.after(POLL_INTERVAL, self._poll_rx)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    def _send(self, cmd: str):
        if not (self._serial and self._serial.is_open):
            return
        try:
            self._serial.write((cmd + "\n").encode("utf-8"))
            self._log_line("TX", cmd)
        except serial.SerialException as exc:
            self._log_line("ERR", str(exc))
            self._disconnect()

    def _toggle_led(self):
        self._led_on = not self._led_on
        if self._led_on:
            self._send("LED:ON")
            self._led_btn.configure(text="LED  ON", fg_color="#2a7a3b", hover_color="#358a47")
        else:
            self._send("LED:OFF")
            self._led_btn.configure(text="LED  OFF", fg_color="#444", hover_color="#555")

    def _send_solenoid(self):
        self._send("SOLENOID")

    # ------------------------------------------------------------------
    # Log console
    # ------------------------------------------------------------------
    def _log_line(self, direction: str, text: str):
        ts   = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] {direction:<3}  {text}\n"
        self._log.configure(state="normal")
        self._log.insert("end", line)
        self._log.see("end")
        self._log.configure(state="disabled")

    # ------------------------------------------------------------------
    # Window close
    # ------------------------------------------------------------------
    def _on_close(self):
        self._disconnect()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
