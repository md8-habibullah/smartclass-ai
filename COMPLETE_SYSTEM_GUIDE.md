╔════════════════════════════════════════════════════════════════╗
║ AI CLASSROOM MONITOR — COMPLETE SETUP ║
║ For ESP32-CAM + ESP32 OLED + Python Server ║
╚════════════════════════════════════════════════════════════════╝

# ✅ WHAT'S READY NOW

1. ✅ Python server.py running on laptop (http://localhost:5000)
2. ✅ Hotspot "Spider" created and active (IP: 10.42.0.1)
3. ✅ Dashboard with:
   - Live video feed from ESP32-CAM
   - Real-time engagement score + metrics
   - Emotion breakdown charts
   - Captured frames gallery (every 5 seconds)
   - OLED alert status
4. ✅ Image capture system:
   - Saves every frame with face detection boxes
   - Stores in ~/cccoding/SAC/captured_images/
   - Shows in dashboard gallery
   - Displays metadata (timestamp, score, students, emotions)
5. ✅ API endpoints for Arduino boards:
   - /register_cam — ESP32-CAM auto-registers
   - /api/score — OLED polls every 5 seconds
   - /api/captures — Dashboard displays galleries

# 📋 NEXT STEPS: UPLOAD ARDUINO CODE

YOU HAVE 2 NEW INSTRUCTION FILES:

1. 📄 ESP32_CAM_INSTRUCTIONS.md
   Location: ~/cccoding/SAC/ESP32_CAM_INSTRUCTIONS.md
   → Complete step-by-step guide to upload camera code
   → Code is ready to copy-paste into Arduino IDE
   → Includes troubleshooting guide

2. 📄 ESP32_OLED_INSTRUCTIONS.md
   Location: ~/cccoding/SAC/ESP32_OLED_INSTRUCTIONS.md
   → Complete guide for teacher OLED display
   → Code ready to copy-paste
   → Includes wiring diagram and library setup

UPLOAD ORDER:
FIRST: ESP32-CAM (esp32cam.ino)
THEN: ESP32 Dev Board (esp32_oled.ino)

# 🎯 EXPECTED BEHAVIOR AFTER UPLOADS

ESP32-CAM Upload Complete:
✓ Serial Monitor shows: "[REG] Registered with server ✓"
✓ Dashboard changes from "Waiting..." to "🟢 Connected"
✓ Live video feed appears in dashboard
✓ Green/orange/red face boxes show emotions
✓ Score updates every 5 seconds
✓ Images saved to captured_images folder

ESP32 OLED Upload Complete:
✓ OLED displays boot animation
✓ Then shows "CLASS MONITOR" with score %
✓ Updates every 5 seconds from server
✓ Shows alert (flashing border) when boring (< 40%)
✓ Badge in dashboard header shows "OLED" as green

# 📸 CAPTURED IMAGES SYSTEM

Location: ~/cccoding/SAC/captured_images/

Files saved every 5 seconds:
• Image: 20260508_155859_65pct_3stu.jpg
• Metadata: 20260508_155859_metadata.txt

Metadata contains:
Timestamp: 2026-05-08_15:58:59
Score: 65%
Students: 3
Emotions: {'happy': 2, 'neutral': 1}

Dashboard Gallery:
✓ Shows last 50 captured images
✓ Click any image for fullscreen view
✓ Shows timestamp, score, student count
✓ Refreshes every 5.5 seconds (after capture)

Per-Person Analysis:
• Each face has its own color box: - 🟢 Green: 70%+ (ENGAGED) - 🟠 Orange: 40-69% (NEUTRAL) - 🔴 Red: <40% (BORING)
• Text above box shows: emotion + score
• Emotion breakdown chart on dashboard

# 🔄 REAL-TIME WORKFLOW

Every 5 seconds:

1.  ESP32-CAM captures frame
2.  Server receives frame via MJPEG stream
3.  DeepFace analyzes all faces
4.  Server annotates frame (boxes + text)
5.  Server saves annotated frame to disk
6.  Server calculates class score + emotions
7.  Dashboard updates live:
    - Video feed refreshes
    - Score/metrics update
    - Gallery adds new image
8.  ESP32 OLED polls /api/score
9.  OLED updates display (if score < 40%, alert)

# 🌐 HOW TO VIEW SYSTEM

Local Laptop:
→ Open browser: http://localhost:5000
→ OR: http://127.0.0.1:5000

From Another Computer (same hotspot):
→ http://10.42.0.1:5000
→ OR: http://<laptop-hostname>:5000

# 📱 HOTSPOT DETAILS

WiFi Name: Spider
Password: spider-ghost
IP Address: 10.42.0.1

Both ESP32 boards connect here:

- ESP32-CAM connects and gets IP like 10.42.0.45
- ESP32 Dev Board gets IP like 10.42.0.98
- Both connect to laptop server at 10.42.0.1:5000

# ⚠️ IMPORTANT NOTES

Server Must Stay Running:
• Keep the terminal running "python server.py"
• If it crashes, restart with: python server.py
• Don't close the terminal

Hotspot Must Stay ON:
• If you turn off hotspot, boards disconnect
• Boards will auto-reconnect when hotspot comes back
• Check status in dashboard header badges

Image Storage:
• Only keeps last 100 captures (auto-deletes old ones)
• Metadata stored as text files
• Folder path: ~/cccoding/SAC/captured_images/

Performance:
• DeepFace is CPU-heavy (analyzes every 5 sec)
• Laptop fans might run hard — normal
• Limit to 15-50 students for smooth performance
• If slow, can increase CAPTURE_EVERY to 10 seconds in server.py

# 📊 DASHBOARD SECTIONS

Header:
✓ Title + Clock
✓ CAM badge (green if connected)
✓ OLED badge (green if polling)

Left Panel:
✓ Big engagement score (0-100%)
✓ Progress bar color-coded
✓ Status pill (ENGAGED/NEUTRAL/BORING)
✓ Metrics: student count, top emotion, scans, last time

Right Panel:
✓ Live video feed with annotated faces
✓ Green/orange/red boxes around detected faces
✓ Emotion label + percentage for each face

Bottom Charts:
✓ Engagement History (line graph, last 40 scans)
✓ Emotion Breakdown (bar chart for each emotion)

Captured Frames Gallery:
✓ Grid of latest 50 images
✓ Shows timestamp, score, student count
✓ Click to expand fullscreen
✓ Auto-scrollable

Alert Banner:
✓ Appears at top if score < 40%
✓ Red flashing border
✓ Message: "LOW ENGAGEMENT DETECTED"

# 🔧 TROUBLESHOOTING QUICK REFERENCE

Problem: "Cannot connect to port 5000"
→ Server might not be running
→ Check terminal: "python server.py"
→ Or: Kill and restart the process

Problem: "Camera stream not loading"
→ ESP32-CAM not connected to hotspot
→ Check Serial Monitor on ESP32-CAM
→ See: ESP32_CAM_INSTRUCTIONS.md

Problem: "OLED stuck on 'Connecting...'"
→ Check hotspot name is "Spider"
→ Check password is "spider-ghost"
→ Check server is running
→ See: ESP32_OLED_INSTRUCTIONS.md

Problem: "Images not saving to captured_images"
→ Folder might not be writable
→ Run: chmod 777 ~/cccoding/SAC/captured_images
→ Check disk space: df -h

Problem: "Slow performance / CPU high"
→ DeepFace is analyzing every 5 seconds
→ Normal for 15-50 person classroom
→ Can increase interval by editing server.py line: CAPTURE_EVERY = 5

# 📝 FILES IN PROJECT

~/cccoding/SAC/
├── server.py ← Main Python server (AI engine)
├── templates/
│ └── dashboard.html ← Web dashboard (live + gallery)
├── esp32cam.ino ← Camera code (copy to Arduino)
├── esp32_oled.ino ← OLED code (copy to Arduino)
├── ESP32_CAM_INSTRUCTIONS.md ← Camera upload guide
├── ESP32_OLED_INSTRUCTIONS.md ← OLED upload guide
├── SETUP.txt ← Basic setup guide
├── captured_images/ ← Auto-created folder for frames
│ ├── 20260508_155859_65pct_3stu.jpg
│ ├── 20260508_155859_metadata.txt
│ └── ... (last 100 images)
└── venv/ ← Python virtual environment

# 🚀 QUICK START CHECKLIST

Before uploading Arduino code:
☐ Server running (terminal shows "Press CTRL+C to quit")
☐ Hotspot ON (check WiFi list for "Spider")
☐ Dashboard loads (http://localhost:5000)
☐ USB cables connected to both ESP32 boards
☐ Arduino IDE open with correct board/port selected

ESP32-CAM Upload:
☐ Code copied into Arduino IDE
☐ Board: "AI Thinker ESP32-CAM"
☐ Port: Correct COM/ttyUSB selected
☐ Press Upload, then RST button when "Connecting..." shows
☐ Serial Monitor shows "[REG] Registered ✓"
☐ Dashboard shows live video

ESP32 OLED Upload:
☐ OLED wired: VCC→3.3V, GND→GND, SDA→21, SCL→22
☐ Libraries installed: Adafruit SSD1306, GFX, ArduinoJson
☐ Code copied into Arduino IDE
☐ Board: "ESP32 Dev Module"
☐ Port: Correct USB port
☐ Upload (no RST button needed)
☐ OLED shows boot animation, then "CLASS MONITOR"
☐ Dashboard header shows "OLED" green badge

Full System Test:
☐ Dashboard shows live video + score
☐ OLED shows real-time engagement %
☐ Put face in camera → score updates
☐ Show neutral/sad face → score drops
☐ Score < 40% → alert on OLED + dashboard
☐ Captured images appear in gallery
☐ Click image → fullscreen view works
☐ Dashboard updates every 2.5 seconds
☐ OLED updates every 5 seconds

# ✅ YOU'RE READY!

Once you upload both Arduino sketches, the complete system will:

1.  Stream live video from ESP32-CAM
2.  Detect all faces and their emotions
3.  Calculate real-time classroom engagement score
4.  Display live on your laptop dashboard
5.  Show engagement percentage on teacher's OLED display
6.  Save annotated images every 5 seconds
7.  Alert when class engagement drops
8.  Track emotion breakdown and history

Good luck! 🚀
