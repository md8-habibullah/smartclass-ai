╔════════════════════════════════════════════════════════════════╗
║ ESP32-CAM MODULE — STEP BY STEP INSTRUCTIONS ║
║ Upload Code to AI Thinker ESP32-CAM (MB) ║
╚════════════════════════════════════════════════════════════════╝

# ⚠️ BEFORE YOU START

✓ Laptop hotspot "Spider" must be ON (Settings → WiFi → Turn On Hotspot)
✓ Python server must be RUNNING (python server.py)
✓ ESP32-CAM-MB connected to laptop via USB cable
✓ Arduino IDE installed on laptop

# STEP 1: Open Arduino IDE

1. Click "Tools" menu
2. Select Board → Search "esp32" → Choose "AI Thinker ESP32-CAM"
3. Select Tools → Port → (choose your USB port: COM3, COM4, /dev/ttyUSB0, etc.)

# STEP 2: Create New Sketch

1. File → New
2. Delete everything in the editor
3. COPY & PASTE the code below (entire block)

═══════════════════════════════════════════════════════════════════
📋 CODE TO COPY & PASTE (Select all → Ctrl+C → Ctrl+V in Arduino)
═══════════════════════════════════════════════════════════════════

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include <HTTPClient.h>

// ─── Hotspot credentials (your laptop) ────
const char* WIFI_SSID = "Spider";
const char* WIFI_PASS = "spider-ghost";

// ─── Laptop server IP on hotspot ──────────
const char\* SERVER_IP = "10.42.0.1";
const int SERVER_PORT = 5000;

// ─── Retry config ─────────────────────────
const int REGISTER_RETRIES = 10;
const int REGISTER_DELAY = 3000;

// ─── Camera pins: AI Thinker ──────────────
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

// ─── MJPEG stream ─────────────────────────
#define PART_BOUNDARY "frame_boundary_xyzabc"
static const char* STREAM_CT = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_SEP = "\r\n--" PART_BOUNDARY "\r\n";
static const char\* STREAM_HDR = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t stream_httpd = NULL;

static esp_err_t stream_handler(httpd_req_t _req) {
camera_fb_t_ fb = NULL;
esp_err_t res = ESP_OK;
uint8_t\* jpg_buf = NULL;
size_t jpg_len = 0;
char part_buf[64];

httpd_resp_set_type(req, STREAM_CT);
httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "\*");

while (true) {
fb = esp_camera_fb_get();
if (!fb) {
Serial.println("[CAM] Capture failed");
res = ESP_FAIL;
} else {
if (fb->format != PIXFORMAT_JPEG) {
bool ok = frame2jpg(fb, 85, &jpg_buf, &jpg_len);
esp_camera_fb_return(fb);
fb = NULL;
if (!ok) { res = ESP_FAIL; }
} else {
jpg_buf = fb->buf;
jpg_len = fb->len;
}
}

    if (res == ESP_OK) {
      size_t hlen = snprintf(part_buf, 64, STREAM_HDR, jpg_len);
      res = httpd_resp_send_chunk(req, STREAM_SEP, strlen(STREAM_SEP));
      if (res == ESP_OK)
        res = httpd_resp_send_chunk(req, part_buf, hlen);
      if (res == ESP_OK)
        res = httpd_resp_send_chunk(req, (const char*)jpg_buf, jpg_len);
    }

    if (fb) { esp_camera_fb_return(fb); fb = NULL; jpg_buf = NULL; }
    else if (jpg_buf) { free(jpg_buf); jpg_buf = NULL; }

    if (res != ESP_OK) {
      Serial.println("[STREAM] Client disconnected");
      break;
    }

}
return res;
}

void startStreamServer() {
httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
cfg.server_port = 80;
cfg.max_uri_handlers = 4;

httpd_uri_t stream_uri = {
.uri = "/stream",
.method = HTTP_GET,
.handler = stream_handler,
.user_ctx = NULL
};

if (httpd_start(&stream_httpd, &cfg) == ESP_OK) {
httpd_register_uri_handler(stream_httpd, &stream_uri);
Serial.println("[HTTP] Stream server started on /stream");
} else {
Serial.println("[HTTP] Stream server FAILED to start");
}
}

// ─── Register with laptop server ──────────
bool registerWithServer(const String& myIP) {
String url = String("http://") + SERVER_IP + ":" + SERVER_PORT + "/register_cam";
String body = "{\"ip\":\"" + myIP + "\"}";

for (int i = 0; i < REGISTER_RETRIES; i++) {
HTTPClient http;
http.begin(url);
http.addHeader("Content-Type", "application/json");
int code = http.POST(body);

    if (code == 200) {
      Serial.println("[REG] Registered with server ✓");
      http.end();
      return true;
    } else {
      Serial.printf("[REG] Attempt %d failed (HTTP %d)\n", i+1, code);
    }
    http.end();
    delay(REGISTER_DELAY);

}
Serial.println("[REG] Stream still running, server may come online later");
return false;
}

void setup() {
Serial.begin(115200);
Serial.println("\n╔══════════════════════════════╗");
Serial.println("║ ESP32-CAM Classroom Monitor ║");
Serial.println("╚══════════════════════════════╝");

// Camera init
camera_config_t cfg;
cfg.ledc_channel = LEDC_CHANNEL_0;
cfg.ledc_timer = LEDC_TIMER_0;
cfg.pin_d0 = Y2_GPIO_NUM; cfg.pin_d1 = Y3_GPIO_NUM;
cfg.pin_d2 = Y4_GPIO_NUM; cfg.pin_d3 = Y5_GPIO_NUM;
cfg.pin_d4 = Y6_GPIO_NUM; cfg.pin_d5 = Y7_GPIO_NUM;
cfg.pin_d6 = Y8_GPIO_NUM; cfg.pin_d7 = Y9_GPIO_NUM;
cfg.pin_xclk = XCLK_GPIO_NUM;
cfg.pin_pclk = PCLK_GPIO_NUM;
cfg.pin_vsync = VSYNC_GPIO_NUM;
cfg.pin_href = HREF_GPIO_NUM;
cfg.pin_sscb_sda = SIOD_GPIO_NUM;
cfg.pin_sscb_scl = SIOC_GPIO_NUM;
cfg.pin_pwdn = PWDN_GPIO_NUM;
cfg.pin_reset = RESET_GPIO_NUM;
cfg.xclk_freq_hz = 20000000;
cfg.pixel_format = PIXFORMAT_JPEG;
cfg.frame_size = FRAMESIZE_SVGA; // 800x600
cfg.jpeg_quality = 10;
cfg.fb_count = 2;

esp_err_t err = esp_camera_init(&cfg);
if (err != ESP_OK) {
Serial.printf("[CAM] Init FAILED: 0x%x\n", err);
Serial.println(">>> Check board selection: AI Thinker ESP32-CAM <<<");
while (true) delay(1000);
}
Serial.println("[CAM] Camera OK ✓");

sensor_t\* s = esp_camera_sensor_get();
s->set_brightness(s, 1);
s->set_contrast(s, 1);
s->set_saturation(s, 0);

// WiFi
Serial.printf("[WiFi] Connecting to '%s'...\n", WIFI_SSID);
WiFi.begin(WIFI_SSID, WIFI_PASS);
WiFi.setSleep(false);

int attempts = 0;
while (WiFi.status() != WL_CONNECTED && attempts < 40) {
delay(500);
Serial.print(".");
attempts++;
}
Serial.println();

if (WiFi.status() != WL_CONNECTED) {
Serial.println("[WiFi] FAILED — check hotspot. Restarting...");
delay(3000);
ESP.restart();
}

String myIP = WiFi.localIP().toString();
Serial.println("[WiFi] Connected ✓");
Serial.println("[WiFi] My IP: " + myIP);

startStreamServer();
Serial.println("[STREAM] http://" + myIP + "/stream");

registerWithServer(myIP);

Serial.println("\n>>> READY — Streaming to server <<<");
}

void loop() {
if (WiFi.status() != WL_CONNECTED) {
Serial.println("[WiFi] Lost connection — restarting...");
delay(1000);
ESP.restart();
}
delay(10000);
}

═══════════════════════════════════════════════════════════════════

# STEP 3: Upload Code

1. Click the Upload button (arrow icon)
2. Wait for "Connecting..." message
3. **IMMEDIATELY press the RST button on the MB board** ← CRITICAL!
4. Wait for "Done uploading" (about 30 seconds)

# STEP 4: Open Serial Monitor

1. Tools → Serial Monitor
2. Set baud rate to **115200** (bottom right)
3. You should see output like:

   ╔══════════════════════════════╗
   ║ ESP32-CAM Classroom Monitor ║
   ╚══════════════════════════════╝

   [CAM] Camera OK ✓
   [WiFi] Connecting to 'Spider'...
   [WiFi] Connected ✓
   [WiFi] My IP: 10.42.0.45
   [HTTP] Stream server started on /stream
   [STREAM] http://10.42.0.45/stream
   [REG] Registered with server ✓

   > > > READY — Streaming to server <<<

# ✅ SUCCESS!

If you see "[REG] Registered with server ✓", the camera is working!

Go to http://localhost:5000 in your browser → you should see:
✓ Live video feed from camera
✓ Green boxes around detected faces
✓ Score and emotion analysis
✓ Captured images saved to laptop

# TROUBLESHOOTING

Problem: "Failed to connect to COM port"
→ Check USB cable is connected
→ Check correct port selected in Tools → Port
→ Try unplugging and replugging USB

Problem: "No such file or directory: /path/to/sketch"
→ This is a path issue, click Upload again

Problem: Board not responding after upload
→ Try pressing RST button manually
→ Click Upload again, watch for "Connecting..." then press RST

Problem: Serial Monitor shows nothing
→ Check baud rate is 115200
→ Board might be restarting, wait 5 seconds

Problem: "FAILED — check hotspot"
→ Hotspot might not be running
→ Check: Ubuntu Settings → WiFi → Is hotspot ON?
→ Verify hotspot name is exactly "Spider"
→ Verify password is exactly "spider-ghost"

Problem: Camera not showing in dashboard
→ Check server logs (the terminal running python server.py)
→ Check Serial Monitor of ESP32-CAM for errors
→ Try refreshing browser (Ctrl+F5)

# WHEN EVERYTHING WORKS:

→ Next: Upload ESP32_OLED code to the ESP32 Dev Board
→ Follow ESP32_OLED_INSTRUCTIONS.md
