// Arduino PC Controller - Firmware
//
// NOTA PIN: Il pin 14 (A0) su Arduino Uno NON supporta PWM hardware.
// I pin PWM hardware su Uno sono: 3, 5, 6, 9, 10, 11.
// Viene usato il PIN 11 per il LED con PWM.
// Il pin 13 è il LED onboard ed è usato per l'impulso.

#define PIN_LED_PWM  11   // PWM hardware OK
#define PIN_PULSE    13   // output impulso 500 ms
#define BAUD_RATE    9600
#define PULSE_MS     500

static bool     pulseActive   = false;
static uint32_t pulseStart    = 0;

void setup() {
  pinMode(PIN_LED_PWM, OUTPUT);
  pinMode(PIN_PULSE,   OUTPUT);
  analogWrite(PIN_LED_PWM, 0);
  digitalWrite(PIN_PULSE, LOW);

  Serial.begin(BAUD_RATE);
  Serial.println(F("READY"));
}

void loop() {
  // --- gestione impulso non-bloccante ---
  if (pulseActive && (millis() - pulseStart >= PULSE_MS)) {
    digitalWrite(PIN_PULSE, LOW);
    pulseActive = false;
  }

  // --- lettura comando dalla seriale ---
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd == F("PING")) {
    Serial.println(F("PONG"));

  } else if (cmd == F("PULSE")) {
    digitalWrite(PIN_PULSE, HIGH);
    pulseActive = true;
    pulseStart  = millis();
    Serial.println(F("OK:PULSE"));

  } else if (cmd.startsWith(F("PWM:"))) {
    String valStr = cmd.substring(4);
    long   val    = valStr.toInt();

    // clamp 0-255
    if (val < 0)   val = 0;
    if (val > 255) val = 255;

    analogWrite(PIN_LED_PWM, (uint8_t)val);
    Serial.print(F("OK:PWM:"));
    Serial.println(val);

  } else {
    Serial.print(F("ERR:UNKNOWN:"));
    Serial.println(cmd);
  }
}
