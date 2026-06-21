<#
================================================================================
 UPLOAD FIRMWARE via USB/CH340 (bootloader urboot) - ATmega328 custom board
================================================================================

 Compila uno sketch Arduino (.ino) e lo carica sulla scheda via USB/CH340,
 sfruttando il bootloader urboot gia' installato. Usa arduino-cli.

 USO:
   .\upload-firmware.ps1                                  # default sotto
   .\upload-firmware.ps1 -SketchPath "C:\path\al\mio.ino" -SerialPort COM4
   .\upload-firmware.ps1 -CompileOnly                     # solo compila, non carica
   .\upload-firmware.ps1 -SerialPort COM4

 PREREQUISITI:
   - arduino-cli installato (https://arduino.github.io/arduino-cli/)
   - Core MiniCore gia' installato (lo hai gia')
   - Scheda collegata via USB (CH340), bootloader urboot funzionante
   - Niente Arduino Uno ISP qui: si carica via seriale/bootloader

 PARAMETRI BOARD (coerenti con la tua config):
   FQBN = MiniCore:avr:328  con: variant=modelNonP, clock 16MHz esterno,
          bootloader urboot UART0, BOD 2.7V
================================================================================
#>

param(
    [string] $SketchPath = "",          # percorso allo sketch .ino (o cartella sketch)
    [string] $SerialPort = "COM4",      # porta del CH340 della scheda
    [switch] $CompileOnly               # compila soltanto, non carica
)

$ErrorActionPreference = "Stop"

# --- FQBN completo con tutte le opzioni board ---
# variant=modelNonP -> ATmega328 liscio (signature 1E 95 14)
# clock=external_16MHz, bootloader=uart0 (urboot), BOD=2v7, eeprom=keep, LTO=Os_flto
$FQBN = "MiniCore:avr:328:variant=modelNonP,bootloader=uart0,clock=external_16MHz,BOD=2v7,eeprom=keep,LTO=Os_flto,pinout=variant_pinout"

Write-Host "=== Upload firmware via USB/CH340 (bootloader urboot) ===" -ForegroundColor Cyan
Write-Host ""

# --- 1. verifica arduino-cli ---
Write-Host "[1] Verifico arduino-cli..." -ForegroundColor Green
# Aggiorna PATH dalla sessione di sistema (necessario nei terminali VSCode)
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")
$cli = Get-Command "arduino-cli" -ErrorAction SilentlyContinue
if (-not $cli) {
    # cerca nei posti comuni
    $candidates = @(
        "C:\Program Files\Arduino CLI\arduino-cli.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\arduino-cli\arduino-cli.exe"),
        (Join-Path $env:ProgramFiles "arduino-cli\arduino-cli.exe"),
        "C:\arduino-cli\arduino-cli.exe"
    )
    $cliPath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($cliPath) {
        $cli = $cliPath
    } else {
        Write-Host "    arduino-cli non trovato." -ForegroundColor Red
        Write-Host "    Installalo da: https://arduino.github.io/arduino-cli/latest/installation/" -ForegroundColor Yellow
        Write-Host "    Su Windows, il modo rapido (PowerShell):" -ForegroundColor Yellow
        Write-Host '      winget install ArduinoSA.CLI' -ForegroundColor Cyan
        Write-Host "    Poi riavvia il terminale e rilancia questo script." -ForegroundColor Yellow
        exit 1
    }
} else {
    $cli = $cli.Source
}
Write-Host "    $cli" -ForegroundColor DarkGray

# --- 2. risolvi lo sketch ---
Write-Host ""
Write-Host "[2] Individuo lo sketch..." -ForegroundColor Green
if ([string]::IsNullOrWhiteSpace($SketchPath)) {
    # cerca un .ino nella cartella corrente o sottocartelle
    $ino = Get-ChildItem -Path (Get-Location) -Recurse -Filter "*.ino" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $ino) {
        Write-Host "    Nessuno sketch .ino trovato nella cartella corrente." -ForegroundColor Red
        Write-Host "    Passa il percorso: -SketchPath ""C:\path\al\mio.ino""" -ForegroundColor Yellow
        exit 1
    }
    $SketchPath = $ino.FullName
}
# arduino-cli vuole la CARTELLA dello sketch (che deve avere lo stesso nome del .ino)
if ($SketchPath -like "*.ino") {
    $SketchDir = Split-Path $SketchPath -Parent
} else {
    $SketchDir = $SketchPath
}
Write-Host "    Sketch: $SketchDir" -ForegroundColor DarkGray
Write-Host "    FQBN  : $FQBN" -ForegroundColor DarkGray

# --- 3. compila ---
Write-Host ""
Write-Host "[3] Compilo..." -ForegroundColor Green
& $cli compile --fqbn $FQBN "$SketchDir"
if ($LASTEXITCODE -ne 0) {
    Write-Host "    ERRORE di compilazione." -ForegroundColor Red
    exit 1
}
Write-Host "    Compilazione OK." -ForegroundColor Green

if ($CompileOnly) {
    Write-Host ""
    Write-Host "(CompileOnly) Non carico. Fine." -ForegroundColor Cyan
    exit 0
}

# --- 4. carica via bootloader (seriale/CH340) ---
Write-Host ""
Write-Host "[4] Carico su $SerialPort via bootloader..." -ForegroundColor Green
Write-Host "    (l'auto-reset del CH340 fa entrare il bootloader da solo)" -ForegroundColor DarkGray
& $cli upload --fqbn $FQBN --port $SerialPort "$SketchDir"
if ($LASTEXITCODE -ne 0) {
    Write-Host "    ERRORE di upload." -ForegroundColor Red
    Write-Host "    Controlla: porta giusta ($SerialPort = CH340), nessun Serial Monitor aperto," -ForegroundColor Yellow
    Write-Host "    bootloader urboot presente, cavo USB dati (non solo carica)." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=== FATTO ===" -ForegroundColor Cyan
Write-Host "Firmware caricato sulla scheda via USB/CH340." -ForegroundColor Green
