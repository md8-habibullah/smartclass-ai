"""
╔══════════════════════════════════════════════════════╗
║         AI CLASSROOM MONITOR — MAIN SERVER           ║
║  Laptop acts as WiFi Hotspot + AI Brain + Dashboard  ║
╚══════════════════════════════════════════════════════╝

HOTSPOT:  SSID=Spider  PASSWORD=spider-ghost
LAPTOP IP (hotspot): usually 10.42.0.1  (run: ip addr show)

HOW IT WORKS:
  1. Run this server on laptop
  2. Turn on laptop hotspot (Spider / spider-ghost)
  3. ESP32-CAM connects → auto-registers its IP with server
  4. Server pulls MJPEG stream → analyzes every 5 seconds
  5. ESP32 OLED connects → polls /api/score → shows on display
"""

import os
import cv2
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, render_template, Response, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO

# ─── Suppress TensorFlow noise ───────────────
os.environ["TF_CPP_MIN_LOG_LEVEL"]    = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"]   = "0"
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"

logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("absl").setLevel(logging.ERROR)

# Import DeepFace after suppressing logs
from deepface import DeepFace  # noqa: E402

# ─── Image capture folder ────────────────────
CAPTURE_FOLDER = Path(__file__).parent / "captured_images"
CAPTURE_FOLDER.mkdir(exist_ok=True)

# ─── Flask app ────────────────────────────────
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ─── Logging setup ───────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("monitor")

# ═════════════════════════════════════════════
#  CONFIG
# ═════════════════════════════════════════════
CAPTURE_EVERY   = 8          # seconds between AI frames
OLED_TIMEOUT    = 15         # seconds before OLED marked "disconnected"
CAM_RETRY_DELAY = 5          # seconds between camera reconnect attempts
SERVER_PORT     = 5000

# Emotion → engagement score
EMOTION_SCORE = {
    "happy":    100,
    "surprise":  75,
    "neutral":   55,
    "fear":      30,
    "sad":       20,
    "angry":     15,
    "disgust":   10,
}

# ═════════════════════════════════════════════
#  IMAGE CAPTURE
# ═════════════════════════════════════════════

def save_capture(annotated_frame, score, students, emotions, timestamp_str):
    """Save annotated frame to captured_images folder with metadata."""
    try:
        # Filename: YYYYMMDD_HHMMSS.jpg
        safe_ts = timestamp_str.replace(":", "").replace("-", "")
        filename = f"{safe_ts}_{score}pct_{students}stu.jpg"
        filepath = CAPTURE_FOLDER / filename
        
        # Save image
        cv2.imwrite(str(filepath), annotated_frame)
        
        # Save metadata as text
        meta_file = CAPTURE_FOLDER / f"{safe_ts}_metadata.txt"
        with open(meta_file, "w") as f:
            f.write(f"Timestamp: {timestamp_str}\n")
            f.write(f"Score: {score}%\n")
            f.write(f"Students: {students}\n")
            f.write(f"Emotions: {emotions}\n")
        
        log.info(f"  ✓ Saved: {filename}")
        
        # Keep only last 100 images (delete old ones)
        images = sorted(CAPTURE_FOLDER.glob("*_*_*.jpg"), reverse=True)
        for old_img in images[100:]:
            try:
                old_img.unlink()
                meta = old_img.parent / f"{old_img.stem.split('_')[0]}_metadata.txt"
                if meta.exists():
                    meta.unlink()
            except:
                pass
        
        return str(filepath)
    except Exception as e:
        log.warning(f"Failed to save capture: {e}")
        return None

# ═════════════════════════════════════════════
#  SHARED STATE  (thread-safe via lock)
# ═════════════════════════════════════════════
_lock = threading.Lock()

state = {
    # Camera
    "cam_ip":         "10.42.0.153",
    "cam_connected":  False,
    "cam_status":     "waiting",   # waiting | connecting | streaming | error

    # AI results
    "score":      0,
    "students":   0,
    "alert":      False,
    "eng_level":  "WAITING",      # WAITING | ENGAGED | NEUTRAL | BORING
    "emotions":   {},
    "history":    [],
    "last_scan":  "--:--:--",
    "scan_count": 0,

    # Live video (annotated frame bytes)
    "frame_bytes": None,
    "latest_frame": None,

    # OLED device
    "oled_last_ping": 0,
    "oled_connected": False,
}


def get_state():
    with _lock:
        return dict(state)


def update_state(**kwargs):
    with _lock:
        state.update(kwargs)

def broadcast_state():
    socket_data = get_state()
    socket_data.pop("frame_bytes", None)
    socket_data.pop("latest_frame", None)
    socketio.emit("update", socket_data)


# ═════════════════════════════════════════════
#  AI ANALYSIS ENGINE
# ═════════════════════════════════════════════

def score_to_level(score: int) -> str:
    if score >= 70:
        return "ENGAGED"
    elif score >= 40:
        return "NEUTRAL"
    else:
        return "BORING"


def analyze_frame(frame):
    """Run DeepFace on a frame. Returns annotated frame + metrics."""
    try:
        results = DeepFace.analyze(
            frame,
            actions=["emotion"],
            enforce_detection=False,
            silent=True,
            detector_backend="mtcnn",  # Changed from mediapipe due to compatibility issues
        )
        if not isinstance(results, list):
            results = [results]

        annotated   = frame.copy()
        total_score = 0
        emo_counts  = {}
        valid_faces = []

        for face in results:
            conf = face.get("face_confidence", 1.0)
            if conf is not None and conf < 0.60:
                continue                          # skip ghost detections
            valid_faces.append(face)

            emotion = face["dominant_emotion"]
            region  = face["region"]
            score   = EMOTION_SCORE.get(emotion, 50)
            total_score += score
            emo_counts[emotion] = emo_counts.get(emotion, 0) + 1

            # Color: green / orange / red
            color = (
                (0, 220, 80)   if score >= 70 else
                (0, 165, 255)  if score >= 40 else
                (0, 50, 240)
            )

            x, y, w, h = region["x"], region["y"], region["w"], region["h"]
            cv2.rectangle(annotated, (x, y), (x+w, y+h), color, 2)
            cv2.putText(
                annotated,
                f"{emotion}  {score}%",
                (x, max(y - 8, 14)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2,
            )

        n   = len(valid_faces)
        avg = round(total_score / n) if n > 0 else 0

        # Header bar
        level   = score_to_level(avg)
        h_color = (0,220,80) if avg >= 70 else (0,165,255) if avg >= 40 else (0,50,240)
        ts      = datetime.now().strftime("%H:%M:%S")

        cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 44), (10, 10, 18), -1)
        cv2.putText(
            annotated,
            f"Students: {n}   Score: {avg}%   [{level}]   {ts}",
            (8, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.72, h_color, 2,
        )

        if avg < 40 and n > 0:
            foot_y = annotated.shape[0] - 10
            cv2.putText(
                annotated,
                "  LOW ENGAGEMENT  Teacher Alert Active",
                (8, foot_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 50, 240), 2,
            )

        return annotated, avg, n, emo_counts, valid_faces

    except Exception as e:
        log.warning(f"DeepFace error: {e}")
        return frame, 0, 0, {}, []


def camera_worker():
    """Background thread: connects to ESP32-CAM, grabs frames continuously."""
    import cv2
    import numpy as np

    # Pre-generate an error frame to show when disconnected
    err_img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(err_img, "Camera Disconnected", (140, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    _, err_buf = cv2.imencode(".jpg", err_img)
    err_frame_bytes = err_buf.tobytes()

    while True:
        cam_ip = state["cam_ip"]

        # ── Wait for ESP32-CAM to register ──
        if not cam_ip:
            update_state(cam_status="waiting", cam_connected=False, frame_bytes=err_frame_bytes)
            broadcast_state()
            time.sleep(1)
            continue

        # ── Connect / reconnect ──
        # Explicitly assigning port 80 for the camera stream
        stream_url = f"http://{cam_ip}:80/stream"
        log.info(f"Connecting to ESP32-CAM → {stream_url}")
        update_state(cam_status="connecting", cam_connected=False, frame_bytes=err_frame_bytes)
        broadcast_state()

        try:
            # Using OpenCV VideoCapture which natively handles MJPEG chunking, buffers, and timeouts perfectly
            import os
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;5000000" # 5 second timeout
            
            cap = cv2.VideoCapture(stream_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # minimize lag

            if not cap.isOpened():
                log.warning(f"Could not open stream via cv2.VideoCapture")
                time.sleep(CAM_RETRY_DELAY)
                continue

            update_state(cam_status="streaming", cam_connected=True)
            broadcast_state()

            while True:
                ret, frame = cap.read()
                if not ret:
                    raise Exception("Stream read failed or disconnected")

                with _lock:
                    if state.get("latest_frame") is None:
                        log.info("Successfully decoded first frame from stream!")
                    state["latest_frame"] = frame
                    
                    # Fetch latest AI info to draw on the live feed
                    last_faces = state.get("last_faces", [])
                    score      = state.get("score", 0)
                    students   = state.get("students", 0)
                    ts         = state.get("last_scan", "--:--:--")

                # -- Draw live AI overlay directly on the fast stream --
                live_frame = frame.copy()
                for face in last_faces:
                    region = face.get("region", {})
                    emotion = face.get("dominant_emotion", "neutral")
                    scr = EMOTION_SCORE.get(emotion, 50)
                    
                    color = (0, 220, 80) if scr >= 70 else (0, 165, 255) if scr >= 40 else (0, 50, 240)
                    
                    if "x" in region:
                        x, y, w, h = region["x"], region["y"], region["w"], region["h"]
                        cv2.rectangle(live_frame, (x, y), (x+w, y+h), color, 2)
                        cv2.putText(live_frame, f"{emotion} {scr}%", (x, max(y - 8, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2)

                # Draw top bar on live stream
                cv2.rectangle(live_frame, (0, 0), (live_frame.shape[1], 44), (10, 10, 18), -1)
                h_color = (0, 220, 80) if score >= 70 else (0, 165, 255) if score >= 40 else (0, 50, 240)
                cv2.putText(live_frame, f"Students: {students}   Score: {score}%   {ts}", (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.72, h_color, 2)

                # Re-encode to JPEG for the dashboard live feed
                ok, jpg_buf = cv2.imencode(".jpg", live_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                if ok:
                    update_state(frame_bytes=jpg_buf.tobytes())

        except Exception as e:
            log.warning(f"Stream connection lost: {e}")
            update_state(cam_status="error", cam_connected=False, frame_bytes=err_frame_bytes)
            broadcast_state()
            if 'cap' in locals() and cap.isOpened():
                cap.release()
            time.sleep(CAM_RETRY_DELAY)


def ai_worker():
    """Background thread: runs AI analysis every few seconds without blocking the stream."""
    while True:
        time.sleep(CAPTURE_EVERY)
        
        with _lock:
            frame = state.get("latest_frame")
            
        if frame is None:
            continue
            
        # Make a copy to avoid reading it while it's being updated
        frame_copy = frame.copy()
        
        ts = datetime.now().strftime("%H:%M:%S")
        ts_full = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log.info(f"Analyzing frame @ {ts} ...")

        annotated, avg, n, emo_counts, valid_faces = analyze_frame(frame_copy)
        level = score_to_level(avg)
        alert = (avg < 40 and n > 0)

        # Save annotated frame to disk
        save_capture(annotated, avg, n, emo_counts, ts_full)

        with _lock:
            state["score"]       = avg
            state["students"]    = n
            state["alert"]       = alert
            state["eng_level"]   = level
            state["emotions"]    = emo_counts
            state["last_faces"]  = valid_faces
            state["last_scan"]   = ts
            state["scan_count"] += 1
            state["history"].append({"time": ts, "score": avg})
            if len(state["history"]) > 40:
                state["history"].pop(0)

            # Push to WebSockets instantly
            broadcast_state()

        log.info(f"  → {n} students | score={avg}% | {level} | alert={alert}")


def oled_watchdog():
    """Periodically check if OLED board is still pinging us."""
    while True:
        now = time.time()
        last = state["oled_last_ping"]
        connected = (last > 0) and (now - last < OLED_TIMEOUT)
        update_state(oled_connected=connected)
        time.sleep(3)


# ═════════════════════════════════════════════
#  MJPEG VIDEO STREAM GENERATOR
# ═════════════════════════════════════════════

def gen_frames():
    while True:
        fb = state["frame_bytes"]
        if fb:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + fb
                + b"\r\n"
            )
        time.sleep(0.04)


# ═════════════════════════════════════════════
#  FLASK ROUTES
# ═════════════════════════════════════════════

@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/video_feed")
def video_feed():
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/register_cam", methods=["POST"])
def register_cam():
    """ESP32-CAM calls this on boot to tell server its IP."""
    data   = request.get_json(silent=True) or {}
    cam_ip = data.get("ip") or request.remote_addr
    log.info(f"ESP32-CAM registered from {cam_ip}")
    update_state(cam_ip=cam_ip)
    return jsonify({"status": "ok", "message": f"Registered {cam_ip}"})


@app.route("/api/score")
def api_score():
    """Lightweight — polled by ESP32 OLED every 5 sec."""
    with _lock:
        update_state(oled_last_ping=time.time())
        return jsonify({
            "score":    state["score"],
            "students": state["students"],
            "alert":    state["alert"],
            "level":    state["eng_level"],
        })


@app.route("/api/data")
def api_data():
    """Full data for browser dashboard."""
    with _lock:
        return jsonify({
            "score":         state["score"],
            "students":      state["students"],
            "alert":         state["alert"],
            "level":         state["eng_level"],
            "emotions":      state["emotions"],
            "history":       state["history"],
            "last_scan":     state["last_scan"],
            "scan_count":    state["scan_count"],
            "cam_connected": state["cam_connected"],
            "cam_status":    state["cam_status"],
            "cam_ip":        state["cam_ip"],
            "oled_connected":state["oled_connected"],
        })


@app.route("/api/set_cam_ip", methods=["POST"])
def set_cam_ip():
    """Manually set cam IP from dashboard if auto-register fails."""
    data = request.get_json(silent=True) or {}
    ip   = data.get("ip", "").strip()
    if ip:
        update_state(cam_ip=ip)
        log.info(f"Cam IP manually set to {ip}")
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "No IP provided"}), 400


@app.route("/api/captures")
def api_captures():
    """Return list of captured images with metadata."""
    images = []
    for img_file in sorted(CAPTURE_FOLDER.glob("*_*_*.jpg"), reverse=True)[:50]:
        meta_file = img_file.parent / f"{img_file.stem.split('_')[0]}_metadata.txt"
        meta = {}
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    for line in f:
                        if ": " in line:
                            key, val = line.split(": ", 1)
                            meta[key.strip()] = val.strip()
            except:
                pass
        
        images.append({
            "filename": img_file.name,
            "timestamp": meta.get("Timestamp", ""),
            "score": meta.get("Score", "--"),
            "students": meta.get("Students", "--"),
            "emotions": meta.get("Emotions", "{}"),
        })
    
    return jsonify({"captures": images})


@app.route("/captured/<filename>")
def serve_capture(filename):
    """Serve a captured image file."""
    try:
        file_path = CAPTURE_FOLDER / filename
        if file_path.exists() and file_path.suffix.lower() == ".jpg":
            return send_file(str(file_path), mimetype="image/jpeg")
    except:
        pass
    return jsonify({"error": "File not found"}), 404


# ═════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════╗
║         AI CLASSROOM MONITOR — STARTING              ║
╠══════════════════════════════════════════════════════╣
║  Hotspot  : Spider / spider-ghost                    ║
║  Dashboard: http://10.42.0.1:5000  (or localhost)    ║
║  OLED API : http://10.42.0.1:5000/api/score          ║
║  CAM Reg  : http://10.42.0.1:5000/register_cam       ║
╚══════════════════════════════════════════════════════╝
""")

    # Start background threads
    threading.Thread(target=camera_worker, daemon=True, name="CameraWorker").start()
    threading.Thread(target=ai_worker, daemon=True, name="AIWorker").start()
    threading.Thread(target=oled_watchdog, daemon=True, name="OLEDWatchdog").start()

    socketio.run(app, host="0.0.0.0", port=SERVER_PORT, debug=False, allow_unsafe_werkzeug=True)
