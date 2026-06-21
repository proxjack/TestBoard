# TestBoard PC Controller

Progetto per controllare la **TestBoard** — scheda custom basata su ATmega328 con bootloader **urboot** — tramite PC via seriale USB (CH340).  
Un'app desktop Python (CustomTkinter) permette di controllare un LED, attivare un impulso solenoide e monitorare il log seriale in tempo reale.

---

## Struttura del progetto

```
TestBoard/
├── Hardware/                    # Progetto Altium Designer (schema + PCB)
├── Firmware/
│   └── Firmware.ino             # Sketch Arduino per ATmega328
├── Software/
│   ├── assets/                  # Logo app (PNG, ICO, webp)
│   ├── dist/
│   │   └── TestBoardController.exe   # App compilata (standalone, no Python richiesto)
│   ├── upload-firmware.ps1      # Script flash firmware via USB/CH340
│   ├── flash-urboot.ps1         # Script flash bootloader urboot via ISP
│   └── .vscode/
│       └── tasks.json           # Task VSCode per compilare e flashare
├── .gitignore
└── README.md
```

---

## Hardware

| Componente | Note |
|---|---|
| TestBoard | ATmega328 + bootloader urboot, CH340 integrato |
| LED + resistore 220 Ω | Collegato al pin **10** |
| Solenoide | Collegato al pin **13** (impulso test 500 ms) |
| Cavo USB | Cavo dati — alimentazione + seriale via CH340 |

### Collegamento

```
TestBoard            Breadboard
─────────            ──────────
Pin 10  ──────────►  Anodo LED (+)
GND     ──────────►  Catodo LED (–) via resistore 220 Ω

Pin 13  ──────────►  Solenoide (impulso HIGH 500 ms, poi LOW)
```

| Pin TestBoard | Direzione | Componente |
|---|---|---|
| 10 | OUTPUT | LED esterno (anodo via 220 Ω) |
| 13 | OUTPUT | Solenoide test (HIGH 500 ms, poi LOW) |
| GND | — | Catodo LED / massa comune |

---

## Prerequisiti

### Driver CH340
Su Windows il driver CH340 potrebbe non essere incluso automaticamente.  
Se la scheda non compare in Device Manager → Porta COM: installa il driver CH340 dal sito del produttore.

### arduino-cli (solo per flashare il firmware)

```powershell
winget install ArduinoSA.CLI
```

Poi riapri il terminale. Verifica con:

```powershell
arduino-cli version
```

MiniCore (core per ATmega328 non-P) deve essere installato:

```powershell
arduino-cli core update-index --additional-urls https://mcudude.github.io/MiniCore/package_MCUdude_MiniCore_index.json
arduino-cli core install MiniCore:avr --additional-urls https://mcudude.github.io/MiniCore/package_MCUdude_MiniCore_index.json
```

---

## Flash firmware

### Via VSCode (metodo consigliato)

1. Apri la cartella `Software/` in VSCode.
2. Collega la TestBoard via USB.
3. `Ctrl+Shift+P` → **Tasks: Run Task** → **Firmware: Compila e carica (USB/CH340)**.
4. Inserisci la porta COM quando richiesto (default: **COM5**).  
   Per trovare la porta: Device Manager → Ports (COM & LPT) → cerca **USB-SERIAL CH340**.

### Via PowerShell (manuale)

```powershell
cd TestBoard\Software
.\upload-firmware.ps1 -SerialPort COM5
```

Parametri opzionali:

| Parametro | Default | Descrizione |
|---|---|---|
| `-SerialPort` | `COM4` | Porta COM del CH340 |
| `-SketchPath` | `../Firmware` | Cartella dello sketch |
| `-CompileOnly` | — | Compila senza caricare |

### Configurazione board (FQBN)

```
MiniCore:avr:328:variant=modelNonP,bootloader=uart0,clock=16MHz_external,BOD=2v7,eeprom=keep,LTO=Os_flto
```

| Opzione | Valore |
|---|---|
| Chip | ATmega328 (non-P, signature `1E 95 14`) |
| Clock | 16 MHz esterno |
| Bootloader | urboot UART0 |
| BOD | 2.7 V |
| EEPROM | preservata al flash |
| LTO | abilitato (`Os_flto`) |

---

## Flash bootloader urboot (solo se necessario)

Operazione una-tantum, richiede un Arduino Uno usato come ISP.

Via VSCode → **Tasks: Run Task**:

| Task | Descrizione |
|---|---|
| Bootloader: Leggi signature + fuse | Read-only — verifica chip senza scrivere |
| Bootloader: Scrivi SOLO i fuse | Scrive i fuse senza toccare il bootloader |
| Bootloader: Flash completo (fuse + urboot) | Riscrive fuse + bootloader urboot |

---

## Avvio app

Eseguire direttamente (nessuna installazione Python richiesta):

```
Software\dist\TestBoardController.exe
```

### Utilizzo

1. Collega la TestBoard via USB.
2. Seleziona la porta COM dal menu a tendina (es. `COM5`).
3. Clicca **Connect** — l'app attende il reset automatico (~2 s) e mostra `● Connected`.
4. **LED OFF / LED ON** — toggle del LED sul pin 10.
5. **Solenoid Test** — impulso HIGH 500 ms sul pin 13.
6. Il log seriale mostra tutti i messaggi TX/RX con timestamp.
7. **Disconnect** (o chiudi la finestra) per rilasciare la porta.

---

## Protocollo seriale

**Impostazioni:** 9600 baud, 8N1, terminatore `\n`

### Comandi (PC → TestBoard)

| Comando | Descrizione |
|---|---|
| `LED:ON` | Accende il LED (pin 10 HIGH) |
| `LED:OFF` | Spegne il LED (pin 10 LOW) |
| `SOLENOID` | Impulso pin 13 HIGH per 500 ms, poi LOW |
| `PING` | Verifica connessione |

### Risposte (TestBoard → PC)

| Risposta | Quando |
|---|---|
| `READY` | All'avvio del firmware |
| `PONG` | In risposta a `PING` |
| `OK:LED:ON` | Conferma LED acceso |
| `OK:LED:OFF` | Conferma LED spento |
| `OK:SOLENOID` | Conferma impulso solenoide avviato |
| `ERR:UNKNOWN:<cmd>` | Comando non riconosciuto |

---

## Logo app

Il logo viene caricato da `Software/assets/Amperry_Logo3.png` all'avvio.  
Su Windows viene usato `Amperry_Logo3.ico` (multi-size 16–256 px) come icona finestra/taskbar.

Per sostituire il logo: sovrascrivere i file in `Software/assets/` e ricompilare l'app.

---

## Palette colori (design system Amperry — UI Audit 2026)

| Ruolo | Hex | Uso |
|---|---|---|
| Canvas | `#0A0B0A` | Sfondo finestra principale |
| Surface | `#141614` | Card sezioni (connessione, controlli, log) |
| Raised | `#1E211E` | Elementi interni alle card |
| Border | `#2A2E2A` | Bordi card e input |
| Text primary | `#F5F6F4` | Label, titoli |
| Text muted | `#A8B0AA` | Sottotitoli, label inattive, log body |
| Text disabled | `#6B7268` | Timestamp, stato disabilitato |
| **Volt 500** | `#01F503` | Pulsante azione primaria, dot "Live" |
| Volt 600 | `#00C702` | Hover pulsante primario |
| Volt 800 | `#0E2A10` | Tint sfondi |
| Amber | `#E5A53A` | Stato "Connecting…" |
| Coral | `#E5604A` | Stato "Connection error" |

---

## Troubleshooting

### Porta COM non visibile nel dropdown
- Verifica di usare un cavo USB **dati** (non solo carica).
- Clicca **↻** per aggiornare la lista porte.
- Device Manager → Ports (COM & LPT): la scheda appare come **USB-SERIAL CH340**.
- Se non compare, installa il driver CH340.

### arduino-cli non trovato durante il flash
- Chiudi e riapri il terminale dopo l'installazione.
- Il task VSCode aggiorna il PATH automaticamente da registro di sistema.

### Errore compilazione — FQBN non valido
- Verifica che MiniCore sia installato: `arduino-cli core list`.
- Deve comparire `MiniCore:avr` nella lista.

### La scheda non risponde dopo Connect
- Attendi i 2 s per l'auto-reset — aspetta `● Connected`.
- Premi il tasto fisico **RESET** sulla scheda con la porta aperta.
- Verifica che nessun altro programma (Serial Monitor Arduino IDE, ecc.) stia usando la stessa porta.

### Il LED non si accende
- Verifica la polarità: anodo al pin **10**, catodo a GND via resistore.
- Verifica il resistore ~220 Ω.
- Invia `PING` — se ricevi `PONG` il firmware funziona, il problema è nel circuito.
