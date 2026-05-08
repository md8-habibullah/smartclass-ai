/*
  ╔═══════════════════════════════════════════╗
  ║  ESP32 Dev Board — Teacher OLED Display   ║
  ║  Board: ESP32 Dev Module (30-pin)         ║
  ║  Display: 0.96" I2C SSD1306 OLED Blue     ║
  ╚═══════════════════════════════════════════╝

  WIRING:
    OLED VCC  →  ESP32 3.3V (NOT 5V!)
    OLED GND  →  ESP32 GND
    OLED SDA  →  ESP32 GPIO 21
    OLED SCL  →  ESP32 GPIO 22

  ARDUINO LIBRARIES (Sketch → Include Library → Manage Libraries):
    ✓ Adafruit SSD1306    (by Adafruit)
    ✓ Adafruit GFX Library (by Adafruit)
    ✓ ArduinoJson          (by Benoit Blanchon, version 6.x)

  UPLOAD:
    1. Tools → Board → "ESP32 Dev Module"
    2. Tools → Partition Scheme → "Default 4MB"
    3. Upload, open Serial Monitor @ 115200
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ─── Hotspot credentials ────────────────────
const char* WIFI_SSID  = "Spider";
const char* WIFI_PASS  = "spider-ghost";

// ─── Laptop server ──────────────────────────
const char* SERVER_IP  = "10.42.0.1";
const int   SERVER_PORT = 5000;

// ─── Timing ─────────────────────────────────
const unsigned long POLL_MS   = 5000;   // poll server every 5 sec
const unsigned long HTTP_TIMEOUT = 4000;

// ─── OLED ────────────────────────────────────
#define OLED_W     128
#define OLED_H      64
#define OLED_RST    -1
#define OLED_ADDR  0x3C

Adafruit_SSD1306 oled(OLED_W, OLED_H, &Wire, OLED_RST);

// ─── State ───────────────────────────────────
struct ClassState {
  int    score    = 0;
  int    overall  = 0;
  int    students = 0;
  bool   alert    = false;
  String level    = "WAITING";
  bool   serverOk = false;
};

ClassState cs;
unsigned long lastPoll = 0;
int blinkTick = 0;


// ═════════════════════════════════════════════
//  OLED SCREENS
// ═════════════════════════════════════════════

void drawBoot(const char* msg) {
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);

  oled.setTextSize(1);
  oled.setCursor(20, 4);
  oled.print("Classroom AI");

  oled.drawLine(0, 14, 127, 14, SSD1306_WHITE);

  oled.setTextSize(1);
  oled.setCursor(4, 20);
  oled.print(msg);

  // Animated dots
  for (int i = 0; i < (blinkTick % 4); i++) {
    oled.fillCircle(30 + i*12, 50, 3, SSD1306_WHITE);
  }
  blinkTick++;
  oled.display();
}

void drawNormal() {
  oled.clearDisplay();

  // ── Top bar ──
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(10, 1);
  oled.print("CLASS MONITOR");
  oled.drawLine(0, 10, 127, 10, SSD1306_WHITE);

  // ── Big score ──
  oled.setTextSize(3);
  String scoreStr = String(cs.score) + "%";
  int sw = scoreStr.length() * 18;
  oled.setCursor((128 - sw) / 2, 14);
  oled.print(scoreStr);

  // ── Overall Avg ──
  oled.setTextSize(1);
  String avgStr = "Overall Avg: " + String(cs.overall) + "%";
  oled.setCursor((128 - (avgStr.length() * 6)) / 2, 40);
  oled.print(avgStr);

  // ── Status line ──
  oled.setTextSize(1);
  oled.setCursor(2, 53);
  oled.print(cs.level.substring(0,8));

  // ── Student count ──
  oled.setCursor(70, 53);
  oled.print("N:");
  oled.print(cs.students);

  // ── Server ok indicator ──
  if (cs.serverOk) {
    oled.fillCircle(122, 3, 3, SSD1306_WHITE);
  } else {
    oled.drawCircle(122, 3, 3, SSD1306_WHITE);
  }

  oled.display();
}

void drawAlert() {
  oled.clearDisplay();
  blinkTick++;

  // Flashing border (every other tick)
  if (blinkTick % 2 == 0) {
    oled.drawRect(0, 0, 128, 64, SSD1306_WHITE);
    oled.drawRect(2, 2, 124, 60, SSD1306_WHITE);
  }

  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);

  // Inverted header
  oled.fillRect(0, 0, 128, 12, SSD1306_WHITE);
  oled.setTextColor(SSD1306_BLACK);
  oled.setCursor(30, 2);
  oled.print("!! ALERT !!");
  oled.setTextColor(SSD1306_WHITE);

  oled.setTextSize(2);
  oled.setCursor(14, 16);
  oled.print("BORING");
  oled.setCursor(14, 34);
  oled.print("CLASS!");

  oled.setTextSize(1);
  oled.setCursor(4, 54);
  oled.print("Score:");
  oled.print(cs.score);
  oled.print("%  N:");
  oled.print(cs.students);

  oled.display();
}

void drawServerError() {
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);

  oled.setCursor(22, 4);
  oled.print("Server Error");
  oled.drawLine(0, 14, 127, 14, SSD1306_WHITE);

  oled.setCursor(4, 20);
  oled.print("Cannot reach laptop");
  oled.setCursor(4, 32);
  oled.print("Check server.py");
  oled.setCursor(4, 44);
  oled.print("is running...");

  oled.setCursor(4, 56);
  oled.print("Retrying in 5s");

  oled.display();
}

void drawWifiError() {
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);

  oled.fillRect(0, 0, 128, 12, SSD1306_WHITE);
  oled.setTextColor(SSD1306_BLACK);
  oled.setCursor(20, 2);
  oled.print("WiFi Reconnect");
  oled.setTextColor(SSD1306_WHITE);

  oled.setCursor(4, 18);
  oled.print("Hotspot: Spider");
  oled.setCursor(4, 30);
  oled.print("Connecting...");

  for (int i = 0; i < (blinkTick % 4); i++) {
    oled.fillCircle(20 + i*16, 50, 4, SSD1306_WHITE);
  }
  blinkTick++;
  oled.display();
}


// ═════════════════════════════════════════════
//  NETWORK
// ═════════════════════════════════════════════

void connectWiFi() {
  Serial.printf("[WiFi] Connecting to '%s'...\n", WIFI_SSID);
  WiFi.disconnect(true);
  delay(500);

  // Hardcode Static IP to 10.42.0.154 for OLED board
  // Disabled statically hardcoding to use DHCP for better hotspot reliability
  // IPAddress local_IP(10, 42, 0, 154);
  // IPAddress gateway(10, 42, 0, 1);
  // IPAddress subnet(255, 255, 255, 0);
  // WiFi.config(local_IP, gateway, subnet);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  WiFi.setSleep(false);

  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 40) {
    drawBoot("Connecting WiFi...");
    delay(600);
    Serial.print(".");
    tries++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("[WiFi] Connected! IP: " + WiFi.localIP().toString());
    drawBoot("WiFi OK!");
    delay(800);
  } else {
    Serial.println("[WiFi] Failed — will retry");
  }
}

void pollServer() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Disconnected");
    drawWifiError();
    connectWiFi();
    return;
  }

  String url = String("http://") + SERVER_IP + ":" + SERVER_PORT + "/api/score";

  HTTPClient http;
  http.begin(url);
  http.setTimeout(HTTP_TIMEOUT);
  int code = http.GET();

  if (code == 200) {
    String body = http.getString();
    Serial.println("[API] " + body);

    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, body);

    if (!err) {
      cs.score    = doc["score"]    | 0;
      cs.overall  = doc["overall"]  | 0;
      cs.students = doc["students"] | 0;
      cs.alert    = doc["alert"]    | false;
      cs.level    = String((const char*)(doc["level"] | "UNKNOWN"));
      cs.serverOk = true;
    } else {
      Serial.println("[API] JSON error: " + String(err.c_str()));
      cs.serverOk = false;
    }
  } else {
    Serial.printf("[API] HTTP error: %d\n", code);
    cs.serverOk = false;
    drawServerError();
    http.end();
    return;
  }

  http.end();
}


// ═════════════════════════════════════════════
//  SETUP & LOOP
// ═════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  Serial.println("\n╔═══════════════════════════════════╗");
  Serial.println("║  ESP32 OLED Teacher Display       ║");
  Serial.println("╚═══════════════════════════════════╝");

  // OLED init
  Wire.begin(21, 22);
  if (!oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("[OLED] Init FAILED — check wiring (SDA=21 SCL=22)!");
    while (true) delay(1000);
  }
  Serial.println("[OLED] Display OK ✓");
  oled.setTextWrap(false);
  drawBoot("Starting...");
  delay(800);

  connectWiFi();
}

void loop() {
  unsigned long now = millis();

  // WiFi watchdog
  if (WiFi.status() != WL_CONNECTED) {
    drawWifiError();
    connectWiFi();
    return;
  }

  // Poll server
  if (now - lastPoll >= POLL_MS) {
    lastPoll = now;
    pollServer();
  }

  // Draw screen
  if (cs.alert && cs.students > 0) {
    drawAlert();
    delay(600);
  } else {
    drawNormal();
    delay(400);
  }
}
