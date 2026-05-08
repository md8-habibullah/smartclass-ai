#include "esp_camera.h"
#include <HTTPClient.h>
#include <WiFi.h>

// ==============================
// WIFI
// ==============================

const char *ssid = "Spider";
const char *password = "spider-ghost";

// ==============================
// SERVER
// ==============================

String serverIP = "10.42.0.1";

WiFiServer server(80);

// ==============================
// CAMERA PINS
// AI Thinker ESP32-CAM
// ==============================

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

// ==============================

void startCamera() {
  camera_config_t config;

  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;

  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;

  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;

  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;

  config.pixel_format = PIXFORMAT_JPEG;

  config.frame_size = FRAMESIZE_VGA;

  config.jpeg_quality = 12;

  config.fb_count = 2;

  esp_err_t err = esp_camera_init(&config);

  if (err != ESP_OK) {
    Serial.println("Camera Init Failed");
    ESP.restart();
  }
}

void registerToServer() {
  HTTPClient http;

  String url = "http://" + serverIP + ":5000/register_cam";

  http.begin(url);

  http.addHeader("Content-Type", "application/json");

  String payload = "{\"ip\":\"" + WiFi.localIP().toString() + "\"}";

  int code = http.POST(payload);

  Serial.print("Register code: ");
  Serial.println(code);

  http.end();
}

void setup() {
  Serial.begin(115200);

  startCamera();

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");

  Serial.println(WiFi.localIP());

  registerToServer();

  server.begin();
}

void loop() {
  WiFiClient client = server.available();

  if (!client) {
    delay(1);
    return;
  }

  String req = client.readStringUntil('\r');

  client.flush();

  if (req.indexOf("GET /stream") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: multipart/x-mixed-replace; boundary=frame");
    client.println();

    while (client.connected()) {
      camera_fb_t *fb = esp_camera_fb_get();

      if (!fb) {
        continue;
      }

      client.println("--frame");
      client.println("Content-Type: image/jpeg");
      client.print("Content-Length: ");

      client.println(fb->len);

      client.println();

      client.write(fb->buf, fb->len);

      client.println();

      esp_camera_fb_return(fb);

      delay(30);
    }
  }

  client.stop();
}