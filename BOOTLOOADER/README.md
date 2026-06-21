# Flash Bootloader urboot — ATmega328 custom board (VS Code)

Pacchetto per riscrivere il bootloader **urboot** sulla scheda custom ATmega328
usando un Arduino Uno come programmatore ISP, direttamente da VS Code.
Replica esattamente cio' che fa Arduino IDE -> Burn Bootloader con MiniCore.

## Specifiche della scheda
- Microcontrollore: **ATmega328 liscio** (signature `1E 95 14`) — NON 328P
- Quarzo esterno 16 MHz + 2x 22pF
- Bootloader: **urboot** (MiniCore, UART0, RX=D0 TX=D1, LED su B5, autobaud)
- Fuse (come scritti dall'IDE): **lock 0xFF, efuse 0xFD, hfuse 0xD7, lfuse 0xF7**
  - Con urboot, hfuse 0xD7 e' corretto (gestione boot diversa da Optiboot)
- USB-UART onboard: CH340C con auto-reset DTR -> 100nF -> RESET

## Cosa contiene
```
vscode-flash-bootloader/
├─ .vscode/
│  └─ tasks.json          # task richiamabili dalla palette di VS Code
├─ flash-urboot.ps1       # script PowerShell che fa il lavoro (via avrdude)
└─ README.md
```

## Prerequisiti hardware (programmazione ISP)
1. Sull'Arduino Uno: carica lo sketch **ArduinoISP**
   (Arduino IDE -> File -> Examples -> 11.ArduinoISP)
2. Metti un **condensatore 10uF tra RESET e GND dell'Uno** (dopo aver caricato lo sketch)
   --> senza questo si ha l'errore "cannot get into sync"
3. Collega Uno -> scheda custom (connettore J1):
   - Uno 13 -> SCK
   - Uno 12 -> MISO
   - Uno 11 -> MOSI
   - Uno 10 -> RESET (NON il RESET dell'Uno!)
   - Uno 5V -> Vcc5V
   - Uno GND -> GND
4. Scollega la USB del CH340 dalla scheda durante il flash ISP (evita doppia alimentazione)

## Come usarlo in VS Code
1. Apri questa cartella in VS Code (File -> Open Folder)
2. Premi **Ctrl+Shift+P** -> digita **"Run Task"** -> invio
   (i task NON hanno il pulsante freccia: si lanciano cosi' o con Ctrl+Shift+B)
3. Scegli un task:
   - **Bootloader: Leggi signature + fuse (read-only)** — diagnosi, non scrive nulla
   - **Bootloader: Scrivi SOLO i fuse** — solo i fuse
   - **Bootloader: Flash completo (fuse + urboot)** — procedura completa (consigliato)
4. Ti viene chiesta la **porta COM dell'Arduino Uno** (default COM3).
   ATTENZIONE: e' la porta dell'UNO, NON quella del CH340 della scheda.
   Verifica in Arduino IDE -> Tools -> Port o in Gestione Dispositivi.
5. Segui le indicazioni nel terminale.

Il task "Flash completo" e' anche il **build task di default**: Ctrl+Shift+B.

## IMPORTANTE: la cartella deve chiamarsi .vscode
VS Code legge i task SOLO da una cartella chiamata esattamente `.vscode`
(con il punto). Se il tasks.json e' in `.claude` o altrove, i task non compaiono.

## Nota sui percorsi con caratteri speciali
Se il percorso del progetto contiene `&` (es. `R&D`), i task con type "shell"
falliscono. Questo pacchetto usa **type "process"** che evita il problema.
In ogni caso, meglio percorsi senza `&` (es. `RandD`).

## Verifica del successo
Al termine, controlla i fuse finali. Poi scollega l'Uno, collega la scheda via
USB e carica uno sketch normalmente con Arduino IDE (porta del CH340, board
MiniCore ATmega328, Variant 328).

## Note
- Lo script trova avrdude e il .hex di urboot automaticamente dentro MiniCore.
- Caricare uno sketch via "Upload Using Programmer" (ISP) sovrascrive il
  bootloader: rilancia "Flash completo" per ripristinarlo.
- Mantieni sempre **Variant = 328** (mai 328P) per via della signature 1E 95 14.

## Uso da linea di comando (senza VS Code)
```powershell
.\flash-urboot.ps1 -ProgrammerPort COM3              # completo
.\flash-urboot.ps1 -ProgrammerPort COM3 -ReadOnly    # solo lettura (diagnosi)
.\flash-urboot.ps1 -ProgrammerPort COM3 -FusesOnly   # solo fuse
.\flash-urboot.ps1 -ProgrammerPort COM3 -NoConfirm   # senza conferme
```
