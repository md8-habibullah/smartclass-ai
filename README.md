# AI Classroom Monitoring System

A robust, real-time edge AI system designed to monitor classroom engagement using an ESP32-CAM and a Flask-based backend server. The system captures continuous live imagery, processes it through deep neural networks to detect faces and analyze emotions, and streams the analyzed metrics to a real-time web dashboard.

## Architecture Overview

The project is structured into two main components:
1. **Edge Client (ESP32-CAM)**: Captures high-resolution images at 5-second intervals and securely transmits them to the server over a local Wi-Fi hotspot using standard HTTP POST requests. This decoupled architecture ensures the microcontroller operates purely as a capture device, preventing PSRAM memory fragmentation and guaranteeing long-term stability.
2. **Central Processing Server (Python/Flask)**: Receives the raw byte streams and places them into a thread-safe queue. A background worker continuously pulls frames from this queue, utilizes the `DeepFace` library (with MTCNN backend) to perform inference, and emits the processed data via `Socket.IO` to the frontend dashboard. 

## Key Features

- **Asynchronous AI Pipeline**: The system utilizes a queue-based processing architecture, ensuring that network requests from the ESP32 never block during heavy AI inference.
- **Real-Time Data Streaming**: Implements WebSocket (`Socket.IO`) technology to push live annotated video frames and JSON statistics to the dashboard without requiring page refreshes.
- **Persistent Data Storage**: Features a built-in SQLite database that persistently logs all historical captures, timestamps, engagement scores, and student counts. 
- **Automated Storage Management**: Automatically prunes the physical image directory and the SQLite database to retain only the 100 most recent captures, preventing unbounded disk space consumption.
- **Interactive UI**: The frontend dashboard includes a horizontal continuous history log, overall session averages, and interactive modals to inspect deep emotional breakdowns for any historical capture.

## Setup Instructions

### Hardware Requirements
- ESP32-CAM Module (AI-Thinker model recommended)
- Laptop/PC to act as the Central Processing Server

### Software Installation

1. Clone this repository and navigate to the project root.
2. Ensure Python 3.10+ is installed on your system.
3. Set up a virtual environment and install the required dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Execution

1. **Start the Hotspot**: Configure your laptop to broadcast a Wi-Fi hotspot with the SSID `Spider` and password `spider-ghost`.
2. **Run the Server**: 
```bash
./venv/bin/python server.py
```
3. **Deploy ESP32**: Flash the `esp32cam.ino` sketch to your ESP32-CAM. Once powered on, it will automatically connect to the hotspot and begin transmitting.
4. **Access Dashboard**: Open your web browser and navigate to `http://localhost:5000` (or `http://10.42.0.1:5000`).

## Database Schema

The persistent storage utilizes SQLite. Upon startup, the server executes the following schema initialization:

```sql
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    score INTEGER,
    students INTEGER,
    alert BOOLEAN,
    emotions TEXT,
    image_path TEXT
);
```

To prevent storage bloat, the backend executes the following pruning mechanism after every capture, retaining only the 100 most recent records:

```sql
SELECT id, image_path FROM history ORDER BY id DESC LIMIT -1 OFFSET 100;
DELETE FROM history WHERE id=?;
```

## Technical Stack
- **Microcontroller**: C++, Arduino Core for ESP32, `esp32-camera` driver
- **Backend**: Python 3, Flask, Flask-SocketIO, SQLite3
- **Machine Learning**: DeepFace, TensorFlow/Keras, OpenCV
- **Frontend**: HTML5, Vanilla CSS3, Javascript, Socket.IO Client
