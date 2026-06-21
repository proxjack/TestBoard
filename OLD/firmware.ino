/*
 * Firmware GPIO Controller
 * 
 * Protocollo seriale (9600 baud, terminatore '\n'):
 * 
 *   MODE:<pin>:<DIGITAL|PWM|INPUT>   -> Configura modalita' pin
 *   SET:<pin>:<value>                -> Imposta valore (0/1 per DIGITAL, 0-255 per PWM)
 *   GET:<pin>                        -> Richiede stato pin
 *   GET_ALL                          -> Richiede stato di tutti i pin configurati
 *   PING                             -> Verifica connessione (risponde PONG)
 * 
 * Risposte:
 *   STATUS:<pin>:<value>             -> Stato di un pin
 *   OK:<comando>                     -> Comando eseguito
 *   ERR:<motivo>                     -> Errore
 *   PONG                             -> Risposta a PING
 *   READY                            -> Inviato al boot
 */

#define MAX_PIN 13
#define MIN_PIN 2

// Modalita' pin: 0 = non configurato, 1 = DIGITAL OUT, 2 = PWM OUT, 3 = INPUT
byte pinMode_state[MAX_PIN + 1];
int pinValue[MAX_PIN + 1];

// Pin che supportano PWM su Arduino Uno/Nano: 3, 5, 6, 9, 10, 11
bool isPwmPin(int pin) {
  return (pin == 3 || pin == 5 || pin == 6 || pin == 9 || pin == 10 || pin == 11);
}

bool isValidPin(int pin) {
  return (pin >= MIN_PIN && pin <= MAX_PIN);
}

String inputString = "";

void setup() {
  pinMode(0, INPUT_PULLUP);
  Serial.begin(9600);
  
  // Inizializza array
  for (int i = 0; i <= MAX_PIN; i++) {
    pinMode_state[i] = 0;
    pinValue[i] = 0;
  }
  
  inputString.reserve(64);
  
  delay(100);
  Serial.println("READY");
}

void loop() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n' || inChar == '\r') {
      if (inputString.length() > 0) {
        executeCommand(inputString);
        inputString = "";
      }
    } else {
      inputString += inChar;
      // Sicurezza: evita overflow
      if (inputString.length() > 60) {
        inputString = "";
        Serial.println("ERR:buffer_overflow");
      }
    }
  }
}

void executeCommand(String cmd) {
  cmd.trim();
  
  if (cmd.length() == 0) return;
  
  // PING
  if (cmd == "PING") {
    Serial.println("PONG");
    return;
  }
  
  // GET_ALL
  if (cmd == "GET_ALL") {
    for (int i = MIN_PIN; i <= MAX_PIN; i++) {
      if (pinMode_state[i] != 0) {
        sendStatus(i);
      }
    }
    Serial.println("OK:GET_ALL");
    return;
  }
  
  // MODE:<pin>:<mode>
  if (cmd.startsWith("MODE:")) {
    int firstColon = cmd.indexOf(':');
    int secondColon = cmd.indexOf(':', firstColon + 1);
    
    if (secondColon == -1) {
      Serial.println("ERR:bad_format");
      return;
    }
    
    int pin = cmd.substring(firstColon + 1, secondColon).toInt();
    String mode = cmd.substring(secondColon + 1);
    mode.trim();
    
    if (!isValidPin(pin)) {
      Serial.println("ERR:invalid_pin");
      return;
    }
    
    if (mode == "DIGITAL") {
      pinMode(pin, OUTPUT);
      digitalWrite(pin, LOW);
      pinMode_state[pin] = 1;
      pinValue[pin] = 0;
    }
    else if (mode == "PWM") {
      if (!isPwmPin(pin)) {
        Serial.println("ERR:pin_not_pwm");
        return;
      }
      pinMode(pin, OUTPUT);
      analogWrite(pin, 0);
      pinMode_state[pin] = 2;
      pinValue[pin] = 0;
    }
    else if (mode == "INPUT") {
      pinMode(pin, INPUT_PULLUP);
      pinMode_state[pin] = 3;
      pinValue[pin] = digitalRead(pin);
    }
    else if (mode == "NONE") {
      pinMode(pin, INPUT);  // alta impedenza, sicuro
      pinMode_state[pin] = 0;
      pinValue[pin] = 0;
    }
    else {
      Serial.println("ERR:invalid_mode");
      return;
    }
    
    Serial.print("OK:MODE:");
    Serial.print(pin);
    Serial.print(":");
    Serial.println(mode);
    return;
  }
  
  // SET:<pin>:<value>
  if (cmd.startsWith("SET:")) {
    int firstColon = cmd.indexOf(':');
    int secondColon = cmd.indexOf(':', firstColon + 1);
    
    if (secondColon == -1) {
      Serial.println("ERR:bad_format");
      return;
    }
    
    int pin = cmd.substring(firstColon + 1, secondColon).toInt();
    int value = cmd.substring(secondColon + 1).toInt();
    
    if (!isValidPin(pin)) {
      Serial.println("ERR:invalid_pin");
      return;
    }
    
    if (pinMode_state[pin] == 1) {
      // DIGITAL
      digitalWrite(pin, value > 0 ? HIGH : LOW);
      pinValue[pin] = value > 0 ? 1 : 0;
      sendStatus(pin);
    }
    else if (pinMode_state[pin] == 2) {
      // PWM
      if (value < 0) value = 0;
      if (value > 255) value = 255;
      analogWrite(pin, value);
      pinValue[pin] = value;
      sendStatus(pin);
    }
    else {
      Serial.println("ERR:pin_not_output");
    }
    return;
  }
  
  // GET:<pin>
  if (cmd.startsWith("GET:")) {
    int pin = cmd.substring(4).toInt();
    
    if (!isValidPin(pin)) {
      Serial.println("ERR:invalid_pin");
      return;
    }
    
    // Se e' input, leggi adesso
    if (pinMode_state[pin] == 3) {
      pinValue[pin] = digitalRead(pin);
    }
    
    sendStatus(pin);
    return;
  }
  
  Serial.print("ERR:unknown_cmd:");
  Serial.println(cmd);
}

void sendStatus(int pin) {
  Serial.print("STATUS:");
  Serial.print(pin);
  Serial.print(":");
  Serial.print(pinValue[pin]);
  Serial.print(":");
  
  switch (pinMode_state[pin]) {
    case 1: Serial.println("DIGITAL"); break;
    case 2: Serial.println("PWM"); break;
    case 3: Serial.println("INPUT"); break;
    default: Serial.println("NONE"); break;
  }
}
