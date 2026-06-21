<#
================================================================================
 FLASH BOOTLOADER URBOOT - ATmega328 (liscio, signature 1E 95 14)
 Scheda custom - programmazione via Arduino Uno come ISP (stk500v1)
================================================================================

 Replica esattamente cio' che fa Arduino IDE -> Burn Bootloader con MiniCore,
 bootloader urboot (UART0, RX=D0 TX=D1, LED su B5, autobaud, watchdog 1s).

 USO:
   .\flash-urboot.ps1                      # default sotto
   .\flash-urboot.ps1 -ProgrammerPort COM7 # porta dell'Uno diversa
   .\flash-urboot.ps1 -FusesOnly           # solo fuse, non il bootloader
   .\flash-urboot.ps1 -ReadOnly            # legge solo signature + fuse
   .\flash-urboot.ps1 -NoConfirm           # niente conferme (automazione)

 PREREQUISITI HARDWARE:
   - Arduino Uno con sketch "ArduinoISP" caricato
   - Condensatore 10uF tra RESET e GND dell'Uno (anti-autoreset)
   - Uno -> scheda: pin10->RESET, 11->MOSI, 12->MISO, 13->SCK, 5V, GND
   - L'Uno (programmatore) sulla porta -ProgrammerPort

 FUSE (come scritti da Arduino IDE per questa config):
   lock=0xFF  efuse=0xFD  hfuse=0xD7  lfuse=0xF7
   NB: con urboot, hfuse 0xD7 e' corretto (gestione boot diversa da Optiboot).
================================================================================
#>

param(
    [string] $ProgrammerPort = "COM3",   # porta dell'ARDUINO UNO (programmatore ISP)
    [switch] $FusesOnly,
    [switch] $ReadOnly,
    [switch] $NoConfirm
)

# --- parametri fissi ---
$BaudISP    = 19200
$Part       = "atmega328"
$Programmer = "stk500v1"
# fuse identici a quelli scritti dall'IDE
$Lock  = "0xFF"
$EFuse = "0xFD"
$HFuse = "0xD7"
$LFuse = "0xF7"

$ErrorActionPreference = "Stop"

function Confirm-Step {
    param([string]$Message)
    if ($NoConfirm) { return $true }
    $a = Read-Host "$Message (s/n)"
    return ($a -match '^[sS]')
}

Write-Host "=== Flash urboot - ATmega328 via ISP ===" -ForegroundColor Cyan
Write-Host "Porta programmatore (Arduino Uno): $ProgrammerPort" -ForegroundColor DarkGray
Write-Host ""

# --- 1. trova avrdude ---
Write-Host "[1] Cerco avrdude..." -ForegroundColor Green
$arduino15 = Join-Path $env:LOCALAPPDATA "Arduino15"
$avrdude = Get-ChildItem -Path (Join-Path $arduino15 "packages\MiniCore\tools\avrdude") `
    -Recurse -Filter "avrdude.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $avrdude) {
    $avrdude = Get-ChildItem -Path $arduino15 -Recurse -Filter "avrdude.exe" `
        -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $avrdude) { Write-Host "ERRORE: avrdude.exe non trovato." -ForegroundColor Red; exit 1 }
Write-Host "    $avrdude" -ForegroundColor DarkGray

$avrdudeDir  = Split-Path $avrdude -Parent
$avrdudeConf = Get-ChildItem -Path (Split-Path $avrdudeDir -Parent) `
    -Recurse -Filter "avrdude.conf" -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
$confArg = @(); if ($avrdudeConf) { $confArg = @("-C", $avrdudeConf) }

# --- 2. trova bootloader urboot (lo stesso che usa l'IDE) ---
$bootHex = $null
if (-not $FusesOnly -and -not $ReadOnly) {
    Write-Host ""
    Write-Host "[2] Cerco il bootloader urboot (atmega328, UART0, B5)..." -ForegroundColor Green
    $bootDir = Join-Path $arduino15 "packages\MiniCore\hardware\avr"
    # percorso dal log dell'IDE: .../bootloaders/urboot/atmega328/.../uart0_rxd0_txd1/led+b5/urboot_atmega328_pr_ee_ce.hex
    $cands = Get-ChildItem -Path $bootDir -Recurse -Filter "urboot_atmega328*.hex" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "urboot" -and $_.FullName -match "uart0" -and $_.FullName -match "b5" -and $_.FullName -match "pr_ee_ce" }
    if (-not $cands) {
        # fallback: qualsiasi urboot atmega328 uart0
        $cands = Get-ChildItem -Path $bootDir -Recurse -Filter "urboot_atmega328*.hex" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "uart0" }
    }
    if ($cands) {
        $bootHex = $cands | Select-Object -First 1 -ExpandProperty FullName
        Write-Host "    $bootHex" -ForegroundColor DarkGray
        if ($cands.Count -gt 1) {
            Write-Host "    (trovati $($cands.Count) candidati, uso il primo)" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "    .hex urboot non trovato: scrivo solo i fuse." -ForegroundColor Yellow
        Write-Host "    Completa poi con Arduino IDE -> Burn Bootloader." -ForegroundColor Yellow
    }
}

function Invoke-Avrdude {
    param([string[]]$ExtraArgs, [string]$Label)
    Write-Host ""
    Write-Host ">>> $Label" -ForegroundColor Cyan
    $a = $confArg + @("-p",$Part,"-c",$Programmer,"-P",$ProgrammerPort,"-b",$BaudISP,"-v") + $ExtraArgs
    & $avrdude @a
    return $LASTEXITCODE
}

# --- 3. signature ---
Write-Host ""
Write-Host "[3] Leggo signature (attesa: 1E 95 14)..." -ForegroundColor Green
if ((Invoke-Avrdude -ExtraArgs @() -Label "Signature") -ne 0) {
    Write-Host "ERRORE: nessuna connessione. Controlla ArduinoISP, cap 10uF, cablaggio, porta." -ForegroundColor Red
    exit 1
}

# --- 4. fuse attuali ---
Write-Host ""
Write-Host "[4] Fuse ATTUALI..." -ForegroundColor Green
Invoke-Avrdude -ExtraArgs @("-U","lfuse:r:-:h","-U","hfuse:r:-:h","-U","efuse:r:-:h") -Label "Fuse attuali" | Out-Null

if ($ReadOnly) { Write-Host "`n(ReadOnly) Nessuna scrittura. Fine." -ForegroundColor Cyan; exit 0 }

Write-Host ""
Write-Host "    Target: lock=$Lock efuse=$EFuse hfuse=$HFuse lfuse=$LFuse" -ForegroundColor Yellow
if (-not (Confirm-Step "Procedo con la scrittura?")) { Write-Host "Annullato."; exit 0 }

# --- 5. scrivi fuse (stesso ordine/flag dell'IDE: erase + lock + fuses) ---
Write-Host ""
Write-Host "[5] Scrivo fuse + lock (con chip erase)..." -ForegroundColor Green
if ((Invoke-Avrdude -ExtraArgs @(
        "-e",
        "-U","lock:w:${Lock}:m",
        "-U","efuse:w:${EFuse}:m",
        "-U","hfuse:w:${HFuse}:m",
        "-U","lfuse:w:${LFuse}:m"
    ) -Label "Scrittura fuse + lock + erase") -ne 0) {
    Write-Host "ERRORE scrittura fuse." -ForegroundColor Red; exit 1
}

# --- 5b. bootloader ---
if (-not $FusesOnly -and $bootHex) {
    Write-Host ""
    Write-Host "[5b] Scrivo il bootloader urboot..." -ForegroundColor Green
    if ((Invoke-Avrdude -ExtraArgs @(
            "-U","flash:w:`"$bootHex`":i",
            "-U","lock:w:${Lock}:m"
        ) -Label "Bootloader + lock") -ne 0) {
        Write-Host "ERRORE scrittura bootloader. Usa Arduino IDE -> Burn Bootloader." -ForegroundColor Red; exit 1
    }
}

# --- 6. verifica ---
Write-Host ""
Write-Host "[6] Fuse DOPO scrittura..." -ForegroundColor Green
Invoke-Avrdude -ExtraArgs @("-U","lfuse:r:-:h","-U","hfuse:r:-:h","-U","efuse:r:-:h") -Label "Fuse finali" | Out-Null

Write-Host ""
Write-Host "=== FATTO ===" -ForegroundColor Cyan
Write-Host "Bootloader urboot scritto. Scollega l'Uno e prova l'upload via USB/CH340." -ForegroundColor Green
