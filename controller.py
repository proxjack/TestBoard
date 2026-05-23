"""
Arduino PC Controller — GUI con CustomTkinter + pyserial
Dipendenze: pip install customtkinter pyserial
"""

import time
import queue
import threading
from datetime import datetime

import serial
import serial.tools.list_ports
import customtkinter as ctk

# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------
BAUD_RATE      = 9600
POLL_INTERVAL  = 50   # ms — quanto spesso il main thread svuota la coda RX
DEBOUNCE_MS    = 30   # ms — debounce slider PWM
RESET_DELAY    = 2.0  # secondi — attesa reset Arduino dopo apertura porta


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Arduino PC Controller")
        self.resizable(False, False)

        self._serial: serial.Serial | None = None
        self._rx_queue: queue.Queue[str]   = queue.Queue()
        self._rx_thread: threading.Thread | None = None
        self._debounce_id: str | None      = None   # after() job id per debounce

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_rx()   # avvia il loop di lettura coda

    # ------------------------------------------------------------------
    # Costruzione UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # --- riga porta seriale ---
        row_port = ctk.CTkFrame(self, fg_color="transparent")
        row_port.pack(fill="x", **pad)

        ctk.CTkLabel(row_port, text="Porta:").pack(side="left")

        self._port_var = ctk.StringVar(value="")
        self._port_menu = ctk.CTkOptionMenu(
            row_port, variable=self._port_var,
            values=self._list_ports(), width=160
        )
        self._port_menu.pack(side="left", padx=(6, 0))

        self._refresh_btn = ctk.CTkButton(
            row_port, text="↻", width=36,
            command=self._refresh_ports
        )
        self._refresh_btn.pack(side="left", padx=(4, 0))

        self._connect_btn = ctk.CTkButton(
            row_port, text="Connetti", width=110,
            command=self._toggle_connection
        )
        self._connect_btn.pack(side="left", padx=(10, 0))

        # --- label stato ---
        self._status_label = ctk.CTkLabel(
            self, text="● Disconnesso",
            text_color="#e05555", font=ctk.CTkFont(size=13, weight="bold")
        )
        self._status_label.pack(**pad)

        # --- separatore ---
        ctk.CTkFrame(self, height=2, fg_color="#333").pack(fill="x", padx=12, pady=2)

        # --- slider PWM ---
        row_pwm = ctk.CTkFrame(self, fg_color="transparent")
        row_pwm.pack(fill="x", **pad)

        ctk.CTkLabel(row_pwm, text="Luminosità LED (PWM):").pack(side="left")

        self._pwm_val_label = ctk.CTkLabel(row_pwm, text="0", width=36)
        self._pwm_val_label.pack(side="right")

        self._slider = ctk.CTkSlider(
            self, from_=0, to=255, number_of_steps=255,
            command=self._on_slider_change
        )
        self._slider.set(0)
        self._slider.configure(state="disabled")
        self._slider.pack(fill="x", padx=12, pady=(0, 8))

        # --- pulsante PULSE ---
        self._pulse_btn = ctk.CTkButton(
            self, text="Impulso 500 ms (pin 13)",
            command=self._send_pulse,
            state="disabled"
        )
        self._pulse_btn.pack(**pad)

        # --- separatore ---
        ctk.CTkFrame(self, height=2, fg_color="#333").pack(fill="x", padx=12, pady=2)

        # --- console log ---
        ctk.CTkLabel(self, text="Log seriale", font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=12, pady=(6, 0)
        )

        self._log = ctk.CTkTextbox(
            self, width=460, height=180,
            font=ctk.CTkFont(family="Courier New", size=11),
            state="disabled"
        )
        self._log.pack(padx=12, pady=(2, 12))

    # ------------------------------------------------------------------
    # Porte seriali
    # ------------------------------------------------------------------
    def _list_ports(self) -> list[str]:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        return ports if ports else ["(nessuna porta)"]

    def _refresh_ports(self):
        ports = self._list_ports()
        self._port_menu.configure(values=ports)
        self._port_var.set(ports[0])

    # ------------------------------------------------------------------
    # Connessione / disconnessione
    # ------------------------------------------------------------------
    def _toggle_connection(self):
        if self._serial and self._serial.is_open:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self._port_var.get()
        if not port or port == "(nessuna porta)":
            self._log_line("SYS", "Nessuna porta selezionata.")
            return

        try:
            self._serial = serial.Serial(port, BAUD_RATE, timeout=0.1)
        except serial.SerialException as exc:
            self._log_line("ERR", str(exc))
            return

        self._log_line("SYS", f"Porta aperta: {port} — attendo reset Arduino…")
        # Il reset avviene in un thread per non bloccare la GUI
        threading.Thread(target=self._post_connect_init, daemon=True).start()

    def _post_connect_init(self):
        time.sleep(RESET_DELAY)
        if self._serial and self._serial.is_open:
            self._serial.reset_input_buffer()
        # Aggiorna UI dal main thread
        self.after(0, self._on_connected)

    def _on_connected(self):
        self._connect_btn.configure(text="Disconnetti")
        self._status_label.configure(text="● Connesso", text_color="#55e075")
        self._slider.configure(state="normal")
        self._pulse_btn.configure(state="normal")
        self._log_line("SYS", "Pronto. In ascolto…")

        # Avvia thread di lettura RX
        self._rx_thread = threading.Thread(
            target=self._rx_worker, daemon=True
        )
        self._rx_thread.start()

    def _disconnect(self):
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

        self._connect_btn.configure(text="Connetti")
        self._status_label.configure(text="● Disconnesso", text_color="#e05555")
        self._slider.configure(state="disabled")
        self._pulse_btn.configure(state="disabled")
        self._log_line("SYS", "Disconnesso.")

    # ------------------------------------------------------------------
    # Thread RX — mette le righe ricevute in coda
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
    # Polling coda RX dal main thread
    # ------------------------------------------------------------------
    def _poll_rx(self):
        try:
            while True:
                line = self._rx_queue.get_nowait()
                if line == "__SERIAL_ERROR__":
                    self._log_line("ERR", "Errore seriale — disconnessione.")
                    self._disconnect()
                else:
                    self._log_line("RX", line)
        except queue.Empty:
            pass
        self.after(POLL_INTERVAL, self._poll_rx)

    # ------------------------------------------------------------------
    # Invio comandi
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

    def _send_pulse(self):
        self._send("PULSE")

    # ------------------------------------------------------------------
    # Slider PWM con debounce
    # ------------------------------------------------------------------
    def _on_slider_change(self, value: float):
        val = int(value)
        self._pwm_val_label.configure(text=str(val))

        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)

        self._debounce_id = self.after(
            DEBOUNCE_MS,
            lambda v=val: self._send(f"PWM:{v}")
        )

    # ------------------------------------------------------------------
    # Log console
    # ------------------------------------------------------------------
    def _log_line(self, direction: str, text: str):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] {direction:<3}  {text}\n"

        self._log.configure(state="normal")
        self._log.insert("end", line)
        self._log.see("end")
        self._log.configure(state="disabled")

    # ------------------------------------------------------------------
    # Chiusura applicazione
    # ------------------------------------------------------------------
    def _on_close(self):
        self._disconnect()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
