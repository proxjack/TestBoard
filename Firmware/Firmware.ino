// TestBoard PC Controller - Firmware
// Target: TestBoard (ATmega328P with Arduino bootloader)
//
// Pin 10 — LED digital output (ON/OFF toggle)
// Pin 9 — solenoid test output, HIGH for <ms> then LOW

#define PIN_LED       10
#define PIN_SOLENOID  9
#define BAUD_RATE     9600
#define SOLENOID_MS   500

static bool     solenoidActive = false;
static uint32_t solenoidStart  = 0;
static uint32_t solenoidDur    = SOLENOID_MS;

void setup() {
  pinMode(PIN_LED,      OUTPUT);
  pinMode(PIN_SOLENOID, OUTPUT);
  digitalWrite(PIN_LED,      LOW);
  digitalWrite(PIN_SOLENOID, LOW);

  Serial.begin(BAUD_RATE);
  Serial.println(F("READY"));
}

void loop() {
  // Non-blocking solenoid timing
  if (solenoidActive && (millis() - solenoidStart >= solenoidDur)) {
    digitalWrite(PIN_SOLENOID, LOW);
    digitalWrite(PIN_LED,      LOW);
    solenoidActive = false;
  }

  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd == F("PING")) {
    Serial.println(F("PONG"));

  } else if (cmd == F("LED:ON")) {
    digitalWrite(PIN_LED, HIGH);
    Serial.println(F("OK:LED:ON"));

  } else if (cmd == F("LED:OFF")) {
    digitalWrite(PIN_LED, LOW);
    Serial.println(F("OK:LED:OFF"));

  } else if (cmd.startsWith(F("SOLENOID:"))) {
    // SOLENOID:<ms>  — impulso con durata personalizzata
    uint32_t ms = (uint32_t)cmd.substring(9).toInt();
    if (ms == 0) ms = SOLENOID_MS;
    solenoidDur    = ms;
    digitalWrite(PIN_SOLENOID, HIGH);
    digitalWrite(PIN_LED,      HIGH);
    solenoidActive = true;
    solenoidStart  = millis();
    Serial.print(F("OK:SOLENOID:"));
    Serial.println(ms);

  } else if (cmd == F("SOLENOID")) {
    // Compatibilità: usa durata di default
    solenoidDur    = SOLENOID_MS;
    digitalWrite(PIN_SOLENOID, HIGH);
    digitalWrite(PIN_LED,      HIGH);
    solenoidActive = true;
    solenoidStart  = millis();
    Serial.println(F("OK:SOLENOID"));

  } else {
    Serial.print(F("ERR:UNKNOWN:"));
    Serial.println(cmd);
  }
}
