// TestBoard PC Controller - Firmware
// Target: TestBoard (ATmega328P with Arduino bootloader)
//
// Pin 11 — LED digital output (ON/OFF toggle)
// Pin 13 — pulse output, HIGH for 500 ms then LOW

#define PIN_LED    11
#define PIN_PULSE  13
#define BAUD_RATE  9600
#define PULSE_MS   500

static bool     pulseActive = false;
static uint32_t pulseStart  = 0;

void setup() {
  pinMode(PIN_LED,   OUTPUT);
  pinMode(PIN_PULSE, OUTPUT);
  digitalWrite(PIN_LED,   LOW);
  digitalWrite(PIN_PULSE, LOW);

  Serial.begin(BAUD_RATE);
  Serial.println(F("READY"));
}

void loop() {
  // Non-blocking pulse timing
  if (pulseActive && (millis() - pulseStart >= PULSE_MS)) {
    digitalWrite(PIN_PULSE, LOW);
    pulseActive = false;
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

  } else if (cmd == F("PULSE")) {
    digitalWrite(PIN_PULSE, HIGH);
    pulseActive = true;
    pulseStart  = millis();
    Serial.println(F("OK:PULSE"));

  } else {
    Serial.print(F("ERR:UNKNOWN:"));
    Serial.println(cmd);
  }
}
