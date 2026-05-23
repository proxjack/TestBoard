// TestBoard PC Controller - Firmware
// Target: TestBoard (ATmega328P with Arduino bootloader)
//
// Pin 14 — LED digital output (ON/OFF toggle)
// Pin 13 — solenoid test output, HIGH for 500 ms then LOW

#define PIN_LED       14
#define PIN_SOLENOID  13
#define BAUD_RATE     9600
#define SOLENOID_MS   500

static bool     solenoidActive = false;
static uint32_t solenoidStart  = 0;

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
  if (solenoidActive && (millis() - solenoidStart >= SOLENOID_MS)) {
    digitalWrite(PIN_SOLENOID, LOW);
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

  } else if (cmd == F("SOLENOID")) {
    digitalWrite(PIN_SOLENOID, HIGH);
    solenoidActive = true;
    solenoidStart  = millis();
    Serial.println(F("OK:SOLENOID"));

  } else {
    Serial.print(F("ERR:UNKNOWN:"));
    Serial.println(cmd);
  }
}
