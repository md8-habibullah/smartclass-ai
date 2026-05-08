"""
AI CLASSROOM MONITOR — STABLE QUEUE ARCHITECTURE
"""
import os
import cv2
import time
import queue
import base64
import logging
import numpy as np
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

# Suppress TensorFlow noise
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("absl").setLevel(logging.ERROR)

from deepface import DeepFace

# ─── Flask App Configuration ────────────────────────────────
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

logging.basicConfig(level=logging.INFO, format="%(asctime)s  [%(levelname)s]  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("monitor")

# ─── Shared State ────────────────────────────────
frame_queue = queue.Queue(maxsize=2) # Keep it small to avoid processing old frames
state_lock = threading.Lock()

app_state = {
    "cam_ip": "Waiting...",
    "last_frame_time": 0,
    "score": 0,
    "students": 0,
    "scan_count": 0,
    "last_scan": "--:--:--",
    "alert": False,
    "emotions": {},
    "cam_status": "offline"
}

EMOTION_SCORE = {
    "happy":    100,
    "surprise":  75,
    "neutral":   55,
    "fear":      30,
    "sad":       20,
    "angry":     15,
    "disgust":   10,
}

def score_to_level(score):
    if score >= 70: return "ENGAGED"
    elif score >= 40: return "NEUTRAL"
    else: return "BORING"

# ─── DeepFace AI Worker Thread ────────────────────────────────
def ai_worker():
    log.info("AI Worker thread started.")
    while True:
        try:
            # Block until a frame is available in the queue
            frame_bytes = frame_queue.get(timeout=1)
        except queue.Empty:
            continue

        try:
            # Decode JPEG
            np_img = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
            
            if frame is None:
                log.warning("Received invalid image data.")
                continue

            ts = datetime.now().strftime("%H:%M:%S")
            log.info(f"Analyzing new frame at {ts}...")

            # Run DeepFace
            results = DeepFace.analyze(
                frame,
                actions=["emotion"],
                enforce_detection=False,
                silent=True,
                detector_backend="mtcnn"
            )
            if not isinstance(results, list):
                results = [results]

            annotated = frame.copy()
            total_score = 0
            emo_counts = {}
            valid_faces = []

            for face in results:
                conf = face.get("face_confidence", 1.0)
                if conf is not None and conf < 0.60:
                    continue  # skip low confidence

                valid_faces.append(face)
                emotion = face["dominant_emotion"]
                region = face["region"]
                score = EMOTION_SCORE.get(emotion, 50)
                
                total_score += score
                emo_counts[emotion] = emo_counts.get(emotion, 0) + 1

                # Colors
                color = (0, 220, 80) if score >= 70 else (0, 165, 255) if score >= 40 else (0, 50, 240)

                x, y, w, h = region["x"], region["y"], region["w"], region["h"]
                cv2.rectangle(annotated, (x, y), (x+w, y+h), color, 2)
                cv2.putText(annotated, f"{emotion} {score}%", (x, max(y - 8, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2)

            n = len(valid_faces)
            avg_score = round(total_score / n) if n > 0 else 0
            level = score_to_level(avg_score)
            alert = (avg_score < 40 and n > 0)

            # Draw HUD
            cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 44), (10, 10, 18), -1)
            h_color = (0, 220, 80) if avg_score >= 70 else (0, 165, 255) if avg_score >= 40 else (0, 50, 240)
            cv2.putText(annotated, f"Students: {n}   Score: {avg_score}%   [{level}]   {ts}", (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.72, h_color, 2)

            if alert:
                foot_y = annotated.shape[0] - 10
                cv2.putText(annotated, "LOW ENGAGEMENT  Teacher Alert Active", (8, foot_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 50, 240), 2)

            # Encode to base64 for WebSockets
            _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            b64_img = base64.b64encode(buffer).decode('utf-8')
            img_data = f"data:image/jpeg;base64,{b64_img}"

            # Update State
            with state_lock:
                app_state["score"] = avg_score
                app_state["students"] = n
                app_state["scan_count"] += 1
                app_state["last_scan"] = ts
                app_state["alert"] = alert
                app_state["emotions"] = emo_counts

                # Emit to Socket.IO
                socketio.emit('live_stream', {'image': img_data})
                socketio.emit('analysis_update', app_state)

        except Exception as e:
            log.warning(f"DeepFace processing error: {e}")


# ─── Camera Watchdog ────────────────────────────────
def camera_watchdog():
    """Checks if we haven't received frames in 15 seconds"""
    while True:
        time.sleep(5)
        with state_lock:
            now = time.time()
            if app_state["last_frame_time"] > 0 and (now - app_state["last_frame_time"] > 15):
                if app_state["cam_status"] != "offline":
                    app_state["cam_status"] = "offline"
                    log.warning("Camera connection lost!")
                    socketio.emit('cam_status', {'status': 'offline'})


# ─── Flask Routes ────────────────────────────────
@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/upload", methods=["POST"])
def upload_frame():
    """Receives HTTP POST from ESP32-CAM every 5 seconds"""
    frame_bytes = request.data
    cam_ip = request.remote_addr

    if not frame_bytes:
        return jsonify({"status": "error", "message": "No data"}), 400

    # Update camera status
    with state_lock:
        app_state["cam_ip"] = cam_ip
        app_state["last_frame_time"] = time.time()
        
        if app_state["cam_status"] != "online":
            app_state["cam_status"] = "online"
            log.info(f"Camera online: {cam_ip}")
            socketio.emit('cam_status', {'status': 'online', 'ip': cam_ip})

    # Add frame to processing queue (drop old frame if queue full)
    try:
        frame_queue.put_nowait(frame_bytes)
    except queue.Full:
        try:
            frame_queue.get_nowait() # Remove oldest
            frame_queue.put_nowait(frame_bytes) # Insert newest
        except queue.Empty:
            pass

    return "OK", 200


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║     AI CLASSROOM MONITOR — PORT 5000 RUNNING     ║")
    print("╚══════════════════════════════════════════════════╝")

    threading.Thread(target=ai_worker, daemon=True, name="AIWorker").start()
    threading.Thread(target=camera_watchdog, daemon=True, name="Watchdog").start()

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)