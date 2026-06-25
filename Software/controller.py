"""
TestBoard PC Controller — GUI with CustomTkinter + pyserial
Dependencies: pip install customtkinter pyserial pillow
"""

import os
import sys
import time
import queue
import threading
from datetime import datetime

from PIL import Image, ImageTk
import tkinter as tk

import serial
import serial.tools.list_ports
import customtkinter as ctk

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
_BASE      = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
_LOGO_PATH = os.path.join(_BASE, "assets", "Amperry_Logo3.png")

BAUD_RATE     = 9600
POLL_INTERVAL = 50    # ms — how often the main thread drains the RX queue
RESET_DELAY   = 2.0   # seconds — wait for board auto-reset after port open

# ---------------------------------------------------------------------------
# Design system — Amperry UI Audit 2026
# ---------------------------------------------------------------------------
CANVAS  = "#0A0B0A"
SURFACE = "#141614"
RAISED  = "#1E211E"
BORDER  = "#2A2E2A"
INPUTS  = "#0A0B0A"

TEXT_PRI = "#F5F6F4"
TEXT_MUT = "#A8B0AA"
TEXT_DIS = "#6B7268"

VOLT_500 = "#01F503"
VOLT_600 = "#00C702"
VOLT_800 = "#0E2A10"
AMBER    = "#E5A53A"
CORAL    = "#E5604A"

# System sans-serif per platform; monospace for log output
FONT_SANS = "Segoe UI" if sys.platform == "win32" else "Arial"
FONT_MONO = "Consolas" if sys.platform == "win32" else "Menlo"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TestBoard Controller")
        self.geometry("480x540")
        self.resizable(False, False)
        self.configure(fg_color=CANVAS)

        self._set_app_icon()

        # State
        self._serial:    serial.Serial | None    = None
        self._rx_queue:  queue.Queue[str]        = queue.Queue()
        self._rx_thread: threading.Thread | None = None
        self._led_on:    bool                    = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_rx()

    # ------------------------------------------------------------------
    # App icon (title bar + taskbar)
    # ------------------------------------------------------------------
    def _set_app_icon(self):
        ico_path = os.path.join(_BASE, "assets", "Amperry_Logo3.ico")
        png_path = _LOGO_PATH
        try:
            if sys.platform == "win32" and os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            else:
                icon_img        = Image.open(png_path)
                self.icon_photo = ImageTk.PhotoImage(icon_img)
                self.iconphoto(True, self.icon_photo)
        except Exception as e:
            print(f"Could not load app icon: {e}")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        PH = 20  # outer horizontal padding
        PV = 14  # vertical gap between sections

        # ── HEADER (on canvas — no card) ─────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PH, pady=(24, 0))

        try:
            pil_img  = Image.open(_LOGO_PATH)
            tgt_h    = 64
            tgt_w    = int(tgt_h * pil_img.width / pil_img.height)
            logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(tgt_w, tgt_h))
            logo_lbl = ctk.CTkLabel(header, image=logo_img, text="", fg_color="transparent")
        except Exception:
            logo_lbl = ctk.CTkLabel(
                header, text="A", width=64, height=64,
                fg_color=VOLT_500, text_color="#000000",
                font=ctk.CTkFont(family=FONT_SANS, size=32, weight="bold"),
                corner_radius=8
            )
        logo_lbl.pack(side="left", anchor="center")

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.pack(side="left", padx=(14, 0), anchor="center")

        ctk.CTkLabel(
            title_block, text="TestBoard Controller",
            font=ctk.CTkFont(family=FONT_SANS, size=20, weight="bold"),
            text_color=TEXT_PRI
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_block, text="by Amperry",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            text_color=TEXT_MUT
        ).pack(anchor="w")

        # ── CONNECTION CARD (Surface) ─────────────────────────────────────
        conn_card = ctk.CTkFrame(
            self,
            fg_color=SURFACE,
            border_color=BORDER, border_width=1,
            corner_radius=10
        )
        conn_card.pack(fill="x", padx=PH, pady=(PV, 0))

        conn_row = ctk.CTkFrame(conn_card, fg_color="transparent")
        conn_row.pack(fill="x", padx=16, pady=(14, 0))

        self._port_var = ctk.StringVar(value="")
        self._port_menu = ctk.CTkOptionMenu(
            conn_row,
            variable=self._port_var,
            values=self._list_ports(),
            width=150, height=34,
            fg_color=INPUTS,
            button_color=RAISED,
            button_hover_color=BORDER,
            text_color=TEXT_PRI,
            font=ctk.CTkFont(family=FONT_SANS, size=12),
            corner_radius=6,
            dynamic_resizing=False,
        )
        self._port_menu.pack(side="left")

        # GHOST button — Refresh
        ctk.CTkButton(
            conn_row, text="Refresh", width=68, height=34,
            fg_color="transparent", hover_color=RAISED,
            text_color=TEXT_MUT,
            border_width=0,
            font=ctk.CTkFont(family=FONT_SANS, size=12),
            corner_radius=6,
            command=self._refresh_ports
        ).pack(side="left", padx=(6, 0))

        # PRIMARY button — Connect
        self._connect_btn = ctk.CTkButton(
            conn_row, text="Connect", width=110, height=34,
            fg_color=VOLT_500, hover_color=VOLT_600,
            text_color="#000000",
            border_width=0,
            font=ctk.CTkFont(family=FONT_SANS, size=13, weight="bold"),
            corner_radius=8,
            command=self._toggle_connection
        )
        self._connect_btn.pack(side="left", padx=(10, 0))

        # Status row
        status_row = ctk.CTkFrame(conn_card, fg_color="transparent")
        status_row.pack(fill="x", padx=16, pady=(8, 14))

        self._status_dot = ctk.CTkLabel(
            status_row, text="●", width=14,
            font=ctk.CTkFont(family=FONT_SANS, size=10),
            text_color=TEXT_DIS
        )
        self._status_dot.pack(side="left")

        self._status_label = ctk.CTkLabel(
            status_row, text="Disconnected",
            font=ctk.CTkFont(family=FONT_SANS, size=12),
            text_color=TEXT_MUT
        )
        self._status_label.pack(side="left", padx=(4, 0))

        # ── CONTROLS CARD (Surface) ───────────────────────────────────────
        ctrl_card = ctk.CTkFrame(
            self,
            fg_color=SURFACE,
            border_color=BORDER, border_width=1,
            corner_radius=10
        )
        ctrl_card.pack(fill="x", padx=PH, pady=(PV, 0))

        ctrl_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=16, pady=(14, 14))

        # LED group: state dot + SECONDARY TONALE button
        led_group = ctk.CTkFrame(ctrl_row, fg_color="transparent")
        led_group.pack(side="left")

        self._led_dot = ctk.CTkLabel(
            led_group, text="●", width=14,
            font=ctk.CTkFont(family=FONT_SANS, size=9),
            text_color=TEXT_DIS
        )
        self._led_dot.pack(side="left", padx=(0, 4))

        self._led_btn = ctk.CTkButton(
            led_group, text="LED",
            width=120, height=36,
            fg_color=RAISED, hover_color=BORDER,
            text_color=TEXT_PRI,
            border_color=BORDER, border_width=1,
            font=ctk.CTkFont(family=FONT_SANS, size=13),
            corner_radius=8,
            command=self._toggle_led,
            state="disabled"
        )
        self._led_btn.pack(side="left")

        # PRIMARY button — Solenoid Test, fills remaining width
        self._solenoid_btn = ctk.CTkButton(
            ctrl_row, text="Solenoid Test",
            height=52,
            fg_color=VOLT_500, hover_color=VOLT_600,
            text_color="#000000",
            border_width=0,
            font=ctk.CTkFont(family=FONT_SANS, size=14, weight="bold"),
            corner_radius=8,
            command=self._send_solenoid,
            state="disabled"
        )
        self._solenoid_btn.pack(side="left", padx=(12, 0), fill="x", expand=True)

        # Solenoid pulse duration row
        dur_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        dur_row.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            dur_row, text="Pulse duration (ms):",
            font=ctk.CTkFont(family=FONT_SANS, size=12),
            text_color=TEXT_MUT
        ).pack(side="left")

        self._ms_var = ctk.StringVar(value="5000")
        self._ms_entry = ctk.CTkEntry(
            dur_row,
            textvariable=self._ms_var,
            width=90, height=30,
            fg_color=INPUTS,
            text_color=TEXT_PRI,
            border_color=BORDER, border_width=1,
            font=ctk.CTkFont(family=FONT_SANS, size=12),
            corner_radius=6,
            state="disabled"
        )
        self._ms_entry.pack(side="left", padx=(8, 0))

        # ── LOG CARD (Surface, expands to bottom) ─────────────────────────
        log_card = ctk.CTkFrame(
            self,
            fg_color=SURFACE,
            border_color=BORDER, border_width=1,
            corner_radius=10
        )
        log_card.pack(fill="both", expand=True, padx=PH, pady=(PV, 18))

        # Eyebrow label — uppercase, muted, caption size
        ctk.CTkLabel(
            log_card, text="SERIAL LOG",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            text_color=TEXT_MUT
        ).pack(anchor="w", padx=16, pady=(12, 4))

        # Textbox — Inputs bg (#0A0B0A) recessed into canvas
        self._log = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(family=FONT_MONO, size=11),
            fg_color=INPUTS,
            text_color=TEXT_MUT,
            corner_radius=6,
            border_width=1,
            border_color=BORDER,
            state="disabled"
        )
        self._log.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # Tags for timestamp vs message coloring
        self._log._textbox.tag_configure("ts",  foreground=TEXT_DIS)
        self._log._textbox.tag_configure("txt", foreground=TEXT_MUT)

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
            self._status_dot.configure(text_color=CORAL)
            self._status_label.configure(text="Connection error", text_color=CORAL)
            return

        self._status_dot.configure(text_color=AMBER)
        self._status_label.configure(text="Connecting…", text_color=AMBER)
        self._log_line("SYS", f"Port open: {port} — waiting for board reset…")
        threading.Thread(target=self._post_connect_init, daemon=True).start()

    def _post_connect_init(self):
        time.sleep(RESET_DELAY)
        if self._serial and self._serial.is_open:
            self._serial.reset_input_buffer()
        self.after(0, self._on_connected)

    def _on_connected(self):
        # Connect button → SECONDARY TONALE while connected
        self._connect_btn.configure(
            text="Disconnect",
            fg_color=RAISED, hover_color=BORDER,
            text_color=TEXT_PRI,
            border_color=BORDER, border_width=1
        )
        self._status_dot.configure(text_color=VOLT_500)
        self._status_label.configure(text="Live", text_color=TEXT_PRI)
        self._led_btn.configure(state="normal")
        self._solenoid_btn.configure(state="normal")
        self._ms_entry.configure(state="normal")
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
        # Connect button → PRIMARY
        self._connect_btn.configure(
            text="Connect",
            fg_color=VOLT_500, hover_color=VOLT_600,
            text_color="#000000",
            border_width=0
        )
        self._status_dot.configure(text_color=TEXT_DIS)
        self._status_label.configure(text="Disconnected", text_color=TEXT_MUT)
        self._led_btn.configure(
            text="LED",
            fg_color=RAISED, hover_color=BORDER,
            text_color=TEXT_PRI,
            state="disabled"
        )
        self._led_dot.configure(text_color=TEXT_DIS)
        self._solenoid_btn.configure(state="disabled")
        self._ms_entry.configure(state="disabled")
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
            self._led_dot.configure(text_color=VOLT_500)
        else:
            self._send("LED:OFF")
            self._led_dot.configure(text_color=TEXT_DIS)

    def _send_solenoid(self):
        try:
            ms = max(1, int(self._ms_var.get()))
        except ValueError:
            ms = 5000
        self._send(f"SOLENOID:{ms}")

    # ------------------------------------------------------------------
    # Log — colored timestamps via internal tk.Text tags
    # ------------------------------------------------------------------
    def _log_line(self, direction: str, text: str):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        tb = self._log._textbox
        tb.configure(state="normal")
        tb.insert("end", f"[{ts}] {direction:<3}  ", "ts")
        tb.insert("end", f"{text}\n",                "txt")
        tb.see("end")
        tb.configure(state="disabled")

    # ------------------------------------------------------------------
    # Window close
    # ------------------------------------------------------------------
    def _on_close(self):
        self._disconnect()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
