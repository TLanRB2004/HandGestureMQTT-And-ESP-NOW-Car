#include <WiFi.h>
#include <ESP32MQTTClient.h>
#include <ESP32Servo.h>
#include <mqtt_client.h>
#include <string>

// WiFi and MQTT config
const char* WIFI_SSID = "VKU_Student";
const char* WIFI_PASS = "Vku@2025";
// Đổi thành IP LAN của máy đang chạy MQTT broker local.
const char* BROKER = "192.168.88.106";
const uint16_t PORT = 1883;
const char* CLIENT_ID = "esp32_artemis_car_servo_cpp";
const char* TOPIC = "artemis/robot/command";

// Servo config
static const int SERVO_PIN = 18;
static const int ANGLE_STRAIGHT = 90;
static const int ANGLE_LEFT = 120;
static const int ANGLE_RIGHT = 60;

// Motor driver pins
static const int ENA_PIN = 32;
static const int IN1_PIN = 26;
static const int IN2_PIN = 27;
static const int IN3_PIN = 14;
static const int IN4_PIN = 12;
static const int ENB_PIN = 13;

// Ultrasonic sensor HC-SR04
static const int TRIG_PIN = 19;
static const int ECHO_PIN = 21;
static const int OBSTACLE_CM = 10;
static const uint16_t REVERSE_MS = 300;
static const uint16_t PING_INTERVAL_MS = 60;
static const uint16_t PING_TIMEOUT_MS = 120;
static const uint16_t AVOID_COOLDOWN_MS = 600;

// PWM settings. Use 10-bit resolution to stay close to the MicroPython duty range.
static const int PWM_FREQ = 1000;
static const int PWM_RES_BITS = 10;
static const int PWM_MAX = 1023;
static const int CAR_SPEED_NORMAL = 600;
static const int CAR_SPEED_SLOW = 350;

ESP32MQTTClient mqttClient;
Servo steeringServo;

int currentAngle = ANGLE_STRAIGHT;

volatile uint32_t echoStartUs = 0;
volatile uint32_t echoDurationUs = 0;
volatile bool echoDone = false;
volatile bool echoWaiting = false;

unsigned long lastPingMs = 0;
unsigned long lastAvoidMs = 0;
bool mqttStarted = false;

void setMotorSpeed(int speed) {
  speed = constrain(speed, 0, PWM_MAX);
  ledcWrite(ENA_PIN, speed);
  ledcWrite(ENB_PIN, speed);
}

void driveForward() {
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, HIGH);
  digitalWrite(IN3_PIN, LOW);
  digitalWrite(IN4_PIN, HIGH);
}

void driveBackward() {
  digitalWrite(IN1_PIN, HIGH);
  digitalWrite(IN2_PIN, LOW);
  digitalWrite(IN3_PIN, HIGH);
  digitalWrite(IN4_PIN, LOW);
}

void stopCar() {
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, LOW);
  digitalWrite(IN3_PIN, LOW);
  digitalWrite(IN4_PIN, LOW);
}

void IRAM_ATTR echoIsr() {
  if (digitalRead(ECHO_PIN) == HIGH) {
    echoStartUs = micros();
  } else {
    uint32_t endUs = micros();
    echoDurationUs = endUs - echoStartUs;
    echoDone = true;
    echoWaiting = false;
  }
}

void triggerPing() {
  echoDone = false;
  echoWaiting = true;
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
}

bool checkObstacle(float& distanceCm) {
  if (!echoDone) {
    return false;
  }

  noInterrupts();
  uint32_t duration = echoDurationUs;
  echoDone = false;
  interrupts();

  distanceCm = (duration * 0.0343f) / 2.0f;
  return distanceCm > 0.0f && distanceCm < OBSTACLE_CM;
}

void avoidObstacle() {
  smoothServo(ANGLE_STRAIGHT);
  setMotorSpeed(CAR_SPEED_SLOW);
  driveBackward();
  delay(REVERSE_MS);
  stopCar();
}

void smoothServo(int targetAngle) {
  if (currentAngle == targetAngle) {
    return;
  }

  if (currentAngle < targetAngle) {
    for (int angle = currentAngle; angle <= targetAngle; ++angle) {
      steeringServo.write(angle);
      delay(10);
    }
  } else {
    for (int angle = currentAngle; angle >= targetAngle; --angle) {
      steeringServo.write(angle);
      delay(10);
    }
  }

  currentAngle = targetAngle;
}

void handleCommand(const String& rawCommand) {
  String command = rawCommand;
  command.trim();

  bool isSlow = false;
  if (command.endsWith("_SLOW")) {
    isSlow = true;
    command.remove(command.length() - 5);
  }

  Serial.print("ESP32 received: ");
  Serial.println(rawCommand);

  stopCar();
  setMotorSpeed(isSlow ? CAR_SPEED_SLOW : CAR_SPEED_NORMAL);

  if (command == "FORWARD") {
    smoothServo(ANGLE_STRAIGHT);
    driveForward();
  } else if (command == "BACKWARD") {
    smoothServo(ANGLE_STRAIGHT);
    driveBackward();
  } else if (command == "LEFT") {
    smoothServo(ANGLE_LEFT);
    driveForward();
  } else if (command == "RIGHT") {
    smoothServo(ANGLE_RIGHT);
    driveForward();
  } else if (command == "BACK_LEFT") {
    smoothServo(ANGLE_LEFT);
    driveBackward();
  } else if (command == "BACK_RIGHT") {
    smoothServo(ANGLE_RIGHT);
    driveBackward();
  } else if (command == "STOP") {
    smoothServo(ANGLE_STRAIGHT);
  }
}

void onMessage(const std::string &topic, const std::string &payload) {
  (void)topic;
  String message(payload.c_str());
  handleCommand(message);
}

void onMqttConnect(esp_mqtt_client_handle_t client) {
  if (!mqttClient.isMyTurn(client)) {
    return;
  }

  mqttClient.subscribe(TOPIC, onMessage);
  Serial.print("Subscribed: ");
  Serial.println(TOPIC);
}

#if ESP_IDF_VERSION < ESP_IDF_VERSION_VAL(5, 0, 0)
esp_err_t handleMQTT(esp_mqtt_event_handle_t event) {
  mqttClient.onEventCallback(event);
  return ESP_OK;
}
#else
void handleMQTT(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data) {
  auto *event = static_cast<esp_mqtt_event_handle_t>(event_data);
  mqttClient.onEventCallback(event);
}
#endif

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.print("Connecting WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print('.');
  }

  Serial.println();
  Serial.print("WiFi OK. IP: ");
  Serial.println(WiFi.localIP());
}

void connectMQTT() {
  if (mqttStarted) {
    return;
  }

  String uri = String("mqtt://") + BROKER + ":" + String(PORT);
  mqttClient.setURI(uri.c_str());
  mqttClient.setMqttClientName(CLIENT_ID);
  mqttClient.loopStart();
  mqttStarted = true;
}

void setup() {
  Serial.begin(115200);

  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  pinMode(IN3_PIN, OUTPUT);
  pinMode(IN4_PIN, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  attachInterrupt(digitalPinToInterrupt(ECHO_PIN), echoIsr, CHANGE);

  ledcAttach(ENA_PIN, PWM_FREQ, PWM_RES_BITS);
  ledcAttach(ENB_PIN, PWM_FREQ, PWM_RES_BITS);

  steeringServo.attach(SERVO_PIN, 500, 2400);

  connectWiFi();

  connectMQTT();

  smoothServo(ANGLE_STRAIGHT);
  stopCar();
  setMotorSpeed(CAR_SPEED_NORMAL);
}

void loop() {
  unsigned long nowMs = millis();
  if (!echoWaiting && (nowMs - lastPingMs) >= PING_INTERVAL_MS) {
    triggerPing();
    lastPingMs = nowMs;
  }

  if (echoWaiting && (nowMs - lastPingMs) >= PING_TIMEOUT_MS) {
    echoWaiting = false;
  }

  float distanceCm = 0.0f;
  if (checkObstacle(distanceCm) && (nowMs - lastAvoidMs) >= AVOID_COOLDOWN_MS) {
    lastAvoidMs = nowMs;
    Serial.print("Obstacle detected: ");
    Serial.print(distanceCm, 1);
    Serial.println(" cm");
    avoidObstacle();
  }

  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (!mqttClient.isConnected()) {
    connectMQTT();
  }
  delay(10);
}