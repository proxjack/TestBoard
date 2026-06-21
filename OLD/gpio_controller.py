"""
GPIO Controller - Software PC
Comunica con il firmware Arduino tramite USB seriale.

Permette di:
- Connettersi a una porta seriale
- Aggiungere pin a runtime scegliendone la modalita' (DIGITAL/PWM/INPUT)
- Controllare i pin con pulsanti (digitale) o slider (PWM)
- Leggere lo stato dei pin di input
"""

import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time
import queue

# Pin che supportano PWM su Arduino Uno/Nano
PWM_PINS = {3, 5, 6, 9, 10, 11}
ALL_PINS = list(range(2, 14))


class PinWidget(ctk.CTkFrame):
    """Widget che rappresenta un singolo pin configurato."""
    
    def __init__(self, master, pin, mode, send_callback, remove_callback):
        super().__init__(master, border_width=1)
        self.pin = pin
        self.mode = mode
        self.send_callback = send_callback
        self.remove_callback = remove_callback
        self.current_value = 0
        
        # Layout
        self.grid_columnconfigure(1, weight=1)
        
        # Header: pin + modalita' + rimuovi
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(8, 4))
        header.grid_columnconfigure(1, weight=1)
        
        color = {"DIGITAL": "#3498db", "PWM": "#9b59b6", "INPUT": "#f39c12"}.get(mode, "gray")
        
        ctk.CTkLabel(header, text=f"Pin {pin}", font=("Arial", 16, "bold")).grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text=mode, text_color=color, font=("Arial", 12, "bold")).grid(
            row=0, column=1, sticky="w", padx=10)
        
        ctk.CTkButton(header, text="✕", width=28, height=28,
                      fg_color="#7f8c8d", hover_color="#95a5a6",
                      command=self._on_remove).grid(row=0, column=2, sticky="e")
        
        # Corpo: dipende dalla modalita'
        if mode == "DIGITAL":
            self._build_digital()
        elif mode == "PWM":
            self._build_pwm()
        elif mode == "INPUT":
            self._build_input()
    
    def _build_digital(self):
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.on_btn = ctk.CTkButton(btn_frame, text="ON", fg_color="#2ecc71",
                                     hover_color="#27ae60",
                                     command=lambda: self._set_value(1))
        self.on_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        
        self.off_btn = ctk.CTkButton(btn_frame, text="OFF", fg_color="#e74c3c",
                                      hover_color="#c0392b",
                                      command=lambda: self._set_value(0))
        self.off_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        
        self.state_label = ctk.CTkLabel(self, text="Stato: OFF", text_color="gray")
        self.state_label.grid(row=2, column=0, columnspan=3, pady=(0, 8))
    
    def _build_pwm(self):
        self.value_label = ctk.CTkLabel(self, text="Valore: 0  (0%)",
                                         font=("Arial", 13))
        self.value_label.grid(row=1, column=0, columnspan=3, padx=8, pady=(0, 4))
        
        self.slider = ctk.CTkSlider(self, from_=0, to=255, number_of_steps=255,
                                     command=self._on_slider)
        self.slider.set(0)
        self.slider.grid(row=2, column=0, columnspan=3, padx=8, pady=(0, 4), sticky="ew")
        
        quick_frame = ctk.CTkFrame(self, fg_color="transparent")
        quick_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        quick_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        for i, val in enumerate([0, 64, 128, 255]):
            ctk.CTkButton(quick_frame, text=f"{val}", height=24, width=40,
                          fg_color="#34495e", hover_color="#2c3e50",
                          command=lambda v=val: self._set_value(v)).grid(
                row=0, column=i, padx=2, sticky="ew")
        
        # Debounce per lo slider: invia solo dopo breve pausa
        self._slider_after_id = None
    
    def _build_input(self):
        self.state_label = ctk.CTkLabel(self, text="Stato: ---",
                                         font=("Arial", 14, "bold"))
        self.state_label.grid(row=1, column=0, columnspan=3, padx=8, pady=(0, 4))
        
        ctk.CTkButton(self, text="Leggi Stato", height=28,
                      command=self._read_input).grid(
            row=2, column=0, columnspan=3, padx=8, pady=(0, 8), sticky="ew")
    
    def _on_slider(self, value):
        v = int(value)
        pct = int((v / 255) * 100)
        self.value_label.configure(text=f"Valore: {v}  ({pct}%)")
        
        # Debounce: invia dopo 30ms senza nuovi eventi
        if self._slider_after_id is not None:
            self.after_cancel(self._slider_after_id)
        self._slider_after_id = self.after(30, lambda: self._set_value(v))
    
    def _set_value(self, value):
        self.current_value = value
        self.send_callback(f"SET:{self.pin}:{value}")
        
        if self.mode == "PWM":
            self.slider.set(value)
            pct = int((value / 255) * 100)
            self.value_label.configure(text=f"Valore: {value}  ({pct}%)")
    
    def _read_input(self):
        self.send_callback(f"GET:{self.pin}")
    
    def _on_remove(self):
        self.send_callback(f"MODE:{self.pin}:NONE")
        self.remove_callback(self.pin)
    
    def update_status(self, value):
        """Chiamato quando arriva un STATUS dall'Arduino."""
        self.current_value = value
        if self.mode == "DIGITAL":
            text = "Stato: ON" if value else "Stato: OFF"
            color = "#2ecc71" if value else "gray"
            self.state_label.configure(text=text, text_color=color)
        elif self.mode == "PWM":
            self.slider.set(value)
            pct = int((value / 255) * 100)
            self.value_label.configure(text=f"Valore: {value}  ({pct}%)")
        elif self.mode == "INPUT":
            # Con INPUT_PULLUP: 1 = non premuto, 0 = premuto/a massa
            text = "Stato: HIGH" if value else "Stato: LOW"
            color = "#e67e22" if value else "#3498db"
            self.state_label.configure(text=text, text_color=color)


class GpioControllerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("GPIO Controller")
        self.geometry("700x650")
        ctk.set_appearance_mode("dark")
        
        self.serial_conn = None
        self.rx_thread = None
        self.rx_running = False
        self.rx_queue = queue.Queue()
        self.pin_widgets = {}  # pin -> PinWidget
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self._build_connection_bar()
        self._build_add_pin_bar()
        self._build_pin_area()
        self._build_log_area()
        
        # Avvia il polling della coda RX
        self.after(50, self._process_rx_queue)
        
        # Cleanup alla chiusura
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _build_connection_bar(self):
        bar = ctk.CTkFrame(self)
        bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        bar.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(bar, text="Porta:", font=("Arial", 12, "bold")).grid(
            row=0, column=0, padx=(10, 5), pady=10)
        
        self.port_var = ctk.StringVar(value="Seleziona porta")
        self.port_menu = ctk.CTkOptionMenu(bar, variable=self.port_var,
                                            values=self._get_ports(), width=200)
        self.port_menu.grid(row=0, column=1, padx=5, pady=10, sticky="w")
        
        ctk.CTkButton(bar, text="🔄", width=35,
                      command=self._refresh_ports).grid(row=0, column=2, padx=5, pady=10)
        
        self.connect_btn = ctk.CTkButton(bar, text="Connetti", width=110,
                                          command=self._toggle_connection)
        self.connect_btn.grid(row=0, column=3, padx=5, pady=10)
        
        self.status_label = ctk.CTkLabel(bar, text="● Disconnesso",
                                          text_color="gray", font=("Arial", 12, "bold"))
        self.status_label.grid(row=0, column=4, padx=10, pady=10)
    
    def _build_add_pin_bar(self):
        bar = ctk.CTkFrame(self)
        bar.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(bar, text="Aggiungi Pin:",
                     font=("Arial", 12, "bold")).grid(row=0, column=0, padx=10, pady=10)
        
        self.new_pin_var = ctk.StringVar(value="2")
        self.pin_combo = ctk.CTkOptionMenu(bar, variable=self.new_pin_var,
                                            values=[str(p) for p in ALL_PINS],
                                            width=70,
                                            command=self._on_pin_changed)
        self.pin_combo.grid(row=0, column=1, padx=5, pady=10)
        
        self.new_mode_var = ctk.StringVar(value="DIGITAL")
        self.mode_combo = ctk.CTkOptionMenu(bar, variable=self.new_mode_var,
                                             values=["DIGITAL", "PWM", "INPUT"],
                                             width=110)
        self.mode_combo.grid(row=0, column=2, padx=5, pady=10)
        
        ctk.CTkButton(bar, text="+ Aggiungi", width=110,
                      fg_color="#27ae60", hover_color="#1e8449",
                      command=self._add_pin).grid(row=0, column=3, padx=5, pady=10)
        
        self.pin_hint = ctk.CTkLabel(bar, text="", text_color="gray",
                                       font=("Arial", 11))
        self.pin_hint.grid(row=0, column=4, padx=10, pady=10)
        
        self._on_pin_changed(self.new_pin_var.get())
    
    def _build_pin_area(self):
        container = ctk.CTkFrame(self)
        container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(container, text="Pin configurati",
                     font=("Arial", 14, "bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.pin_scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        self.pin_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 10))
        self.pin_scroll.grid_columnconfigure((0, 1), weight=1)
        
        self.empty_label = ctk.CTkLabel(self.pin_scroll,
                                          text="Nessun pin configurato.\nAggiungi un pin dalla barra in alto.",
                                          text_color="gray", font=("Arial", 12))
        self.empty_label.grid(row=0, column=0, columnspan=2, pady=40)
    
    def _build_log_area(self):
        bar = ctk.CTkFrame(self)
        bar.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
        bar.grid_columnconfigure(0, weight=1)
        
        self.log_text = ctk.CTkTextbox(bar, height=80, font=("Consolas", 11))
        self.log_text.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.log_text.configure(state="disabled")
    
    def _get_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        return ports if ports else ["Nessuna porta"]
    
    def _refresh_ports(self):
        ports = self._get_ports()
        self.port_menu.configure(values=ports)
        if ports and ports[0] != "Nessuna porta":
            self.port_var.set(ports[0])
        self._log(f"Porte rilevate: {', '.join(ports)}")
    
    def _on_pin_changed(self, value):
        try:
            pin = int(value)
            if pin in PWM_PINS:
                self.pin_hint.configure(text="(supporta PWM)", text_color="#9b59b6")
            else:
                self.pin_hint.configure(text="(solo DIGITAL/INPUT)", text_color="gray")
        except ValueError:
            self.pin_hint.configure(text="")
    
    def _toggle_connection(self):
        if self.serial_conn and self.serial_conn.is_open:
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        port = self.port_var.get()
        if port in ("Seleziona porta", "Nessuna porta"):
            self.status_label.configure(text="● Seleziona una porta", text_color="#e74c3c")
            return
        
        try:
            self.status_label.configure(text="● Connessione...", text_color="#f39c12")
            self.update()
            
            self.serial_conn = serial.Serial(port, 9600, timeout=0.1)
            time.sleep(2)  # attesa reset Arduino
            self.serial_conn.reset_input_buffer()
            
            self.rx_running = True
            self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
            self.rx_thread.start()
            
            self.status_label.configure(text=f"● Connesso", text_color="#2ecc71")
            self.connect_btn.configure(text="Disconnetti", fg_color="#e74c3c",
                                         hover_color="#c0392b")
            self._log(f"Connesso a {port}")
            
            # Ping di verifica
            self._send("PING")
        except Exception as e:
            self.status_label.configure(text="● Errore connessione", text_color="#e74c3c")
            self._log(f"ERRORE: {e}")
            self.serial_conn = None
    
    def _disconnect(self):
        self.rx_running = False
        if self.serial_conn and self.serial_conn.is_open:
            try:
                # Resetta tutti i pin a NONE prima di scollegare
                for pin in list(self.pin_widgets.keys()):
                    try:
                        self._send(f"MODE:{pin}:NONE")
                    except Exception:
                        pass
                time.sleep(0.1)
                self.serial_conn.close()
            except Exception:
                pass
        self.serial_conn = None
        
        # Pulisci UI
        for pin in list(self.pin_widgets.keys()):
            self.pin_widgets[pin].destroy()
        self.pin_widgets.clear()
        self._show_empty_label()
        
        self.status_label.configure(text="● Disconnesso", text_color="gray")
        self.connect_btn.configure(text="Connetti", fg_color=["#3a7ebf", "#1f538d"],
                                     hover_color=["#325882", "#14375e"])
        self._log("Disconnesso")
    
    def _send(self, cmd):
        if not self.serial_conn or not self.serial_conn.is_open:
            self._log("ERRORE: non connesso")
            return False
        try:
            self.serial_conn.write(f"{cmd}\n".encode("utf-8"))
            self._log(f"TX: {cmd}")
            return True
        except Exception as e:
            self._log(f"ERRORE TX: {e}")
            return False
    
    def _rx_loop(self):
        """Thread di lettura: legge linee e le mette in coda."""
        buffer = ""
        while self.rx_running and self.serial_conn:
            try:
                if self.serial_conn.in_waiting:
                    data = self.serial_conn.read(self.serial_conn.in_waiting).decode("utf-8", errors="ignore")
                    buffer += data
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self.rx_queue.put(line)
                else:
                    time.sleep(0.02)
            except Exception:
                break
    
    def _process_rx_queue(self):
        """Processa i messaggi RX dal main thread (Tk-safe)."""
        try:
            while True:
                line = self.rx_queue.get_nowait()
                self._handle_rx(line)
        except queue.Empty:
            pass
        self.after(50, self._process_rx_queue)
    
    def _handle_rx(self, line):
        self._log(f"RX: {line}")
        
        if line.startswith("STATUS:"):
            parts = line.split(":")
            if len(parts) >= 3:
                try:
                    pin = int(parts[1])
                    value = int(parts[2])
                    if pin in self.pin_widgets:
                        self.pin_widgets[pin].update_status(value)
                except ValueError:
                    pass
    
    def _add_pin(self):
        if not self.serial_conn or not self.serial_conn.is_open:
            self._log("ERRORE: connettiti prima di aggiungere pin")
            return
        
        try:
            pin = int(self.new_pin_var.get())
        except ValueError:
            return
        
        mode = self.new_mode_var.get()
        
        if pin in self.pin_widgets:
            self._log(f"Pin {pin} gia' configurato. Rimuovilo prima.")
            return
        
        if mode == "PWM" and pin not in PWM_PINS:
            self._log(f"Pin {pin} non supporta PWM. Pin PWM: {sorted(PWM_PINS)}")
            return
        
        # Manda comando MODE all'Arduino
        if not self._send(f"MODE:{pin}:{mode}"):
            return
        
        # Crea widget
        self.empty_label.grid_forget()
        
        widget = PinWidget(self.pin_scroll, pin, mode,
                           send_callback=self._send,
                           remove_callback=self._remove_pin)
        
        # Disponi in griglia 2 colonne
        idx = len(self.pin_widgets)
        widget.grid(row=idx // 2, column=idx % 2, padx=5, pady=5, sticky="nsew")
        
        self.pin_widgets[pin] = widget
    
    def _remove_pin(self, pin):
        if pin in self.pin_widgets:
            self.pin_widgets[pin].destroy()
            del self.pin_widgets[pin]
            self._relayout_pins()
            if not self.pin_widgets:
                self._show_empty_label()
    
    def _relayout_pins(self):
        for idx, (pin, widget) in enumerate(self.pin_widgets.items()):
            widget.grid_forget()
            widget.grid(row=idx // 2, column=idx % 2, padx=5, pady=5, sticky="nsew")
    
    def _show_empty_label(self):
        self.empty_label.grid(row=0, column=0, columnspan=2, pady=40)
    
    def _log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")
        # Limita a ~200 righe
        content = self.log_text.get("1.0", "end")
        lines = content.split("\n")
        if len(lines) > 200:
            self.log_text.delete("1.0", f"{len(lines) - 200}.0")
        self.log_text.configure(state="disabled")
    
    def _on_close(self):
        self.rx_running = False
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    app = GpioControllerApp()
    app.mainloop()
