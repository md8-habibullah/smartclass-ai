#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// --- CONFIGURATION ---
const char* ssid = "Spider";
const char* password = "spider-ghost";
const char* server_url = "http://10.42.0.1:5000/upload";

// AI-Thinker Pin Mapping
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Connected: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nWiFi Connect Failed. Restarting...");
    ESP.restart();
  }
}

void setup() {
  Serial.begin(115200);
  
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

  // Use VGA for balanced performance and memory stability
  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12; 
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    ESP.restart();
  }

  // Pre-warm the camera (sometimes first few frames are green)
  sensor_t *s = esp_camera_sensor_get();
  s->set_vflip(s, 1); // Flip if needed, based on orientation

  connectWiFi();
}

void loop() {
  // Reconnect if connection is lost
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected. Attempting to reconnect...");
    connectWiFi();
  }

  Serial.println("Capturing frame...");
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Capture Failed. Restarting ESP...");
    ESP.restart(); // Extreme measure to ensure long-term stability
    return;
  }

  Serial.printf("Frame captured. Size: %u bytes\n", fb->len);

  // Send image
  HTTPClient http;
  // Increase timeout for slow networks
  http.setTimeout(10000); 
  http.begin(server_url);
  http.addHeader("Content-Type", "image/jpeg");
  http.setReuse(false); // Do not reuse connections to prevent memory leak
  
  int httpResponseCode = http.POST(fb->buf, fb->len);
  
  if (httpResponseCode == 200) {
    Serial.println("Frame sent successfully!");
  } else {
    Serial.printf("Error sending frame. HTTP Status: %d\n", httpResponseCode);
  }
  
  http.end();
  
  // IMMEDIATELY RETURN BUFFER
  esp_camera_fb_return(fb); 
  
  // Wait 5 seconds before next capture
  delay(5000); 
}