╔════════════════════════════════════════════════════════════════╗
║ ESP32 DEV BOARD WITH OLED — STEP BY STEP INSTRUCTIONS ║
║ Teacher Display: Real-time Class Engagement Score ║
╚════════════════════════════════════════════════════════════════╝

# ⚠️ BEFORE YOU START

✓ Hotspot "Spider" must be ON
✓ Python server.py must be RUNNING
✓ ESP32-CAM code already uploaded ✓
✓ OLED display assembled and wired
✓ Arduino IDE with libraries installed

# STEP 1: Wire the OLED Display to ESP32

Use a breadboard + jumper wires to connect:

    OLED Display    →    ESP32 Dev Board
    ─────────────────────────────────────
    VCC (Red)       →    3.3V  (NOT 5V!)
    GND (Black)     →    GND
    SDA (Green)     →    GPIO 21
    SCL (Yellow)    →    GPIO 22

WARNING: Use 3.3V NOT 5V! OLED can be damaged by 5V!

# STEP 2: Install Required Libraries

Open Arduino IDE:

1. Sketch → Include Library → Manage Libraries
2. Search and install EACH of these:

   a) "Adafruit SSD1306"
   - Author: Adafruit
   - Click Install

   b) "Adafruit GFX Library"
   - Author: Adafruit
   - Click Install

   c) "ArduinoJson"
   - Author: Benoit Blanchon
   - Make sure version is 6.x (not 5.x)
   - Click Install

3. Close the library manager

# STEP 3: Setup Arduino for ESP32 Dev Board

1. Tools → Board → Search "ESP32" → Choose "ESP32 Dev Module"
2. Tools → Partition Scheme → "Default 4MB with spiffs"
3. Tools → Port → (your USB port: COM3, COM4, /dev/ttyUSB0)

# STEP 4: Create New Sketch

1. File → New
2. Delete everything
3. COPY & PASTE the code below (entire block)

═══════════════════════════════════════════════════════════════════
📋 CODE TO COPY & PASTE
═══════════════════════════════════════════════════════════════════

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ─── Hotspot credentials ────────────────────
const char* WIFI_SSID = "Spider";
const char* WIFI_PASS = "spider-ghost";

// ─── Laptop server ──────────────────────────
const char\* SERVER_IP = "10.42.0.1";
const int SERVER_PORT = 5000;

// ─── Timing ─────────────────────────────────
const unsigned long POLL_MS = 5000;
const unsigned long HTTP_TIMEOUT = 4000;

// ─── OLED ────────────────────────────────────
#define OLED_W 128
#define OLED_H 64
#define OLED_RST -1
#define OLED_ADDR 0x3C

Adafruit_SSD1306 oled(OLED_W, OLED_H, &Wire, OLED_RST);

// ─── State ───────────────────────────────────
struct ClassState {
int score = 0;
int students = 0;
bool alert = false;
String level = "WAITING";
bool serverOk = false;
};

ClassState cs;
unsigned long lastPoll = 0;
int blinkTick = 0;

void drawBoot(const char\* msg) {
oled.clearDisplay();
oled.setTextColor(SSD1306_WHITE);

oled.setTextSize(1);
oled.setCursor(20, 4);
oled.print("Classroom AI");

oled.drawLine(0, 14, 127, 14, SSD1306_WHITE);

oled.setTextSize(1);
oled.setCursor(4, 20);
oled.print(msg);

for (int i = 0; i < (blinkTick % 4); i++) {
oled.fillCircle(30 + i\*12, 50, 3, SSD1306_WHITE);
}
blinkTick++;
oled.display();
}

void drawNormal() {
oled.clearDisplay();

oled.setTextSize(1);
oled.setTextColor(SSD1306_WHITE);
oled.setCursor(10, 1);
oled.print("CLASS MONITOR");
oled.drawLine(0, 10, 127, 10, SSD1306_WHITE);

oled.setTextSize(3);
String scoreStr = String(cs.score) + "%";
int sw = scoreStr.length() \* 18;
oled.setCursor((128 - sw) / 2, 14);
oled.print(scoreStr);

int barW = map(cs.score, 0, 100, 0, 124);
oled.drawRect(2, 38, 124, 8, SSD1306_WHITE);
oled.fillRect(2, 38, barW, 8, SSD1306_WHITE);

oled.setTextSize(1);
oled.setCursor(2, 49);
oled.print(cs.level.substring(0,8));

oled.setCursor(70, 49);
oled.print("N:");
oled.print(cs.students);

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

if (blinkTick % 2 == 0) {
oled.drawRect(0, 0, 128, 64, SSD1306_WHITE);
oled.drawRect(2, 2, 124, 60, SSD1306_WHITE);
}

oled.setTextSize(1);
oled.setTextColor(SSD1306_WHITE);

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
oled.print("% N:");
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
oled.fillCircle(20 + i\*16, 50, 4, SSD1306_WHITE);
}
blinkTick++;
oled.display();
}

void connectWiFi() {
Serial.printf("[WiFi] Connecting to '%s'...\n", WIFI_SSID);
WiFi.disconnect(true);
delay(500);
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

void setup() {
Serial.begin(115200);
Serial.println("\n╔═══════════════════════════════════╗");
Serial.println("║ ESP32 OLED Teacher Display ║");
Serial.println("╚═══════════════════════════════════╝");

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

if (WiFi.status() != WL_CONNECTED) {
drawWifiError();
connectWiFi();
return;
}

if (now - lastPoll >= POLL_MS) {
lastPoll = now;
pollServer();
}

if (cs.alert && cs.students > 0) {
drawAlert();
delay(600);
} else {
drawNormal();
delay(400);
}
}

═══════════════════════════════════════════════════════════════════

# STEP 5: Upload Code

1. Click Upload button
2. Wait for upload to complete (about 15 seconds)
3. Don't press any buttons this time (unlike ESP32-CAM)

# STEP 6: Open Serial Monitor

1. Tools → Serial Monitor
2. Set baud to 115200
3. You should see:

   ╔═══════════════════════════════════╗
   ║ ESP32 OLED Teacher Display ║
   ╚═══════════════════════════════════╝

   [OLED] Display OK ✓
   [WiFi] Connecting to 'Spider'...
   [WiFi] Connected! IP: 10.42.0.98
   [API] {"score": 65, "students": 3, "alert": false, "level": "ENGAGED"}

# ✅ SUCCESS!

If you see the OLED display showing:

┌─────────────────┐
│ CLASS MONITOR │
│ 65% │
│ ████████░░░░░░ │
│ ENGAGED N: 3 │
└─────────────────┘

Then it's working! The OLED updates every 5 seconds with:
✓ Live class engagement score
✓ Number of students detected
✓ Status (ENGAGED / NEUTRAL / BORING)
✓ Alert animation when class is boring

# ALERT BEHAVIOR

When class engagement drops below 40%, OLED will:

1. Flash a warning border
2. Display "!! ALERT !!" and "BORING CLASS!"
3. Show the score and student count
4. Continue flashing until engagement improves

# TROUBLESHOOTING

Problem: OLED shows nothing (blank screen)
→ Check wiring: SDA→21, SCL→22, VCC→3.3V, GND→GND
→ Check wiring order: maybe SDA/SCL swapped?
→ Try OLED address 0x3D instead of 0x3C (edit line ~32 in code)
→ Check Serial Monitor for "[OLED] Init FAILED" error

Problem: "Cannot reach laptop" error on OLED
→ Hotspot might not be ON
→ Server (python server.py) might not be running
→ Check firewall: might be blocking port 5000
→ Try: curl http://10.42.0.1:5000/api/score (from terminal)

Problem: WiFi says "Connecting..." forever
→ Hotspot "Spider" might not be running
→ Check SSID is exactly "Spider"
→ Check password is exactly "spider-ghost"
→ Try restarting hotspot

Problem: Libraries not found
→ Make sure you installed Adafruit SSD1306, Adafruit GFX, ArduinoJson
→ Check Manage Libraries → search each one
→ Restart Arduino IDE after installing

Problem: Serial Monitor shows "JSON error"
→ Server might not be returning valid data
→ Check server logs (the terminal running python server.py)
→ Make sure ESP32-CAM is already streaming

# WHEN EVERYTHING WORKS:

✓ ESP32-CAM streams video
✓ Dashboard shows live feed with face detection
✓ OLED displays class score
✓ Pictures saved every 5 seconds to laptop
✓ Face-per-person analysis visible

🎉 COMPLETE SYSTEM RUNNING!
