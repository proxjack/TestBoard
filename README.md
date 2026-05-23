# Arduino PC Controller

Progetto minimale per controllare un Arduino Uno/Nano dal PC tramite porta seriale.  
Un'interfaccia grafica Python (CustomTkinter) permette di regolare la luminosità di un LED via PWM e di inviare un impulso digitale, il tutto senza dover toccare codice né Serial Monitor.

---

## Hardware richiesto

| Componente | Note |
|---|---|
| Arduino Uno o Nano | Testato su Uno R3 |
| LED + resistenza da 220 Ω | Collegati sul pin 11 (PWM hardware) |
| Cavo USB | Sia per alimentazione che per seriale |

> **Pin 13** è il LED onboard di Arduino: non serve componente esterno per l'impulso.  
> **Pin 11** è usato per il PWM del LED esterno perché il pin A0 (fisicamente pin 14) non supporta PWM hardware su Arduino Uno.

---

## Schema collegamenti

```
Arduino Uno          Breadboard
───────────          ──────────
Pin 11  ──────────►  Anodo LED (+)
GND     ──────────►  Catodo LED (–) via resistenza 220 Ω

Pin 13  (LED onboard, nessun collegamento esterno richiesto)
```

| Pin Arduino | Direzione | Componente |
|---|---|---|
| 11 | OUTPUT PWM | LED esterno (anodo via 220 Ω) |
| 13 | OUTPUT digitale | LED onboard (impulso 500 ms) |
| GND | — | Catodo LED / riferimento comune |

---

## Installazione

### 1. Firmware — Arduino IDE

1. Apri **Arduino IDE** (versione 1.x o 2.x).
2. Vai su **File → Apri** e seleziona `firmware.ino`.
3. Seleziona la board: **Strumenti → Scheda → Arduino Uno** (o Nano).
4. Seleziona la porta: **Strumenti → Porta → COMx** (Windows) o `/dev/ttyUSBx` (Linux/Mac).
5. Clicca su **Carica** (freccia →).
6. Apri il **Serial Monitor** a 9600 baud e verifica che all'avvio compaia `READY`.

### 2. Software Python

Requisiti: Python 3.10 o superiore.

```bash
# Clona la repo (oppure scarica lo ZIP)
git clone https://github.com/proxjack/test-board.git
cd test-board

# (Opzionale ma consigliato) ambiente virtuale
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Installa le dipendenze
pip install -r requirements.txt

# Avvia il controller
python controller.py
```

---

## Utilizzo

1. Collega Arduino al PC tramite USB.
2. Avvia `python controller.py`.
3. Nel selettore **Porta** scegli la porta seriale di Arduino (es. `COM3` su Windows, `/dev/ttyUSB0` su Linux).
4. Clicca **Connetti** — l'applicazione aspetta 2 secondi per il reset automatico di Arduino, poi mostra `● Connesso`.
5. Trascina lo **slider** (0–255) per regolare la luminosità del LED sul pin 11.
6. Clicca **Impulso 500 ms** per portare il pin 13 HIGH per mezzo secondo (LED onboard lampeggia).
7. Tutti i messaggi TX/RX sono visibili nella console log in basso con timestamp.
8. Clicca **Disconnetti** (o chiudi la finestra) per rilasciare la porta seriale.

---

## Protocollo seriale

**Impostazioni:** 9600 baud, 8N1, terminatore `\n`

### Comandi (PC → Arduino)

| Comando | Descrizione | Esempio |
|---|---|---|
| `PWM:<valore>` | Imposta luminosità LED (0–255). Il valore viene clamped automaticamente. | `PWM:128` |
| `PULSE` | Porta pin 13 HIGH per 500 ms, poi LOW. Non bloccante. | `PULSE` |
| `PING` | Verifica connessione | `PING` |

### Risposte (Arduino → PC)

| Risposta | Quando viene inviata |
|---|---|
| `READY` | All'avvio del firmware |
| `PONG` | In risposta a `PING` |
| `OK:PWM:<n>` | Conferma impostazione PWM (con valore effettivamente applicato) |
| `OK:PULSE` | Conferma avvio impulso |
| `ERR:UNKNOWN:<cmd>` | Comando non riconosciuto |

---

## Struttura del progetto

```
test-board/
├── firmware.ino       # Firmware Arduino (loop non bloccante con millis())
├── controller.py      # GUI Python — CustomTkinter + pyserial
├── requirements.txt   # Dipendenze Python
├── .gitignore         # Esclusioni standard Python
└── README.md          # Questa documentazione
```

---

## Troubleshooting

### La porta seriale non è visibile nel selettore
- Assicurati che il cavo USB sia un cavo **dati** (non solo di ricarica).
- Prova a cliccare **↻** per aggiornare la lista porte.
- Su Windows: controlla in **Gestione dispositivi → Porte (COM e LPT)** se compare `Arduino Uno (COMx)`.
- Installa i driver CH340/CH341 se usi un clone Nano con quel chip USB-seriale.

### Errore di permessi su Linux (`Permission denied: /dev/ttyUSB0`)
Aggiungi il tuo utente al gruppo `dialout` e riavvia la sessione:
```bash
sudo usermod -aG dialout $USER
# poi esegui logout/login oppure:
newgrp dialout
```

### Arduino non risponde dopo la connessione
- L'applicazione aspetta automaticamente 2 secondi per il reset — attendi che lo stato diventi `● Connesso`.
- Se il problema persiste, premi il pulsante **RESET** fisico su Arduino con la porta già aperta.
- Verifica che nessun altro programma (Arduino IDE Serial Monitor, ecc.) stia usando la stessa porta.

### Il LED non si accende
- Controlla la polarità del LED (anodo sul pin 11, catodo verso GND via resistenza).
- Verifica che la resistenza sia ~220 Ω (colori: rosso-rosso-marrone).
- Testa con `PING` → se risponde `PONG` il firmware funziona, il problema è nel circuito.
