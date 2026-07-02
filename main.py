import base64
import time
import threading
import collections
import queue

import cv2
import numpy as np
import torch

from flask import Flask, render_template, request, jsonify
from flask_sock import Sock
from ultralytics import YOLO
import pyttsx3

from simplify import simplify_text, highlight_difficult_words

# =====================
# FLASK
# =====================
app = Flask(__name__, static_folder="static", template_folder="templates")
sock = Sock(app)

# =====================
# DEVICE / YOLO SETUP
# =====================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
INFER_SIZE = 320          # down from default 640 -> big speedup, tune to taste
JPEG_QUALITY = 70         # down from default 95 -> smaller payload, faster send
USE_HALF = DEVICE == "cuda"

print(f"🖥️  Running inference on: {DEVICE}")

model = YOLO("yolov8n.pt")
model.to(DEVICE)

try:
    model.fuse()
except Exception as e:
    print(f"⚠️ Skipping fuse (non-critical): {e}")

if USE_HALF:
    model.half()

# =====================
# OFFLINE TTS (pyttsx3)
# =====================
tts_q = queue.Queue(maxsize=10)


def tts_worker():
    engine = pyttsx3.init()
    engine.setProperty("rate", 145)
    engine.setProperty("volume", 1.0)
    while True:
        text = tts_q.get()
        if text is None:
            break
        engine.say(text)
        engine.runAndWait()


threading.Thread(target=tts_worker, daemon=True).start()

# =====================
# ROUTES
# =====================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/simplify", methods=["POST"])
def simplify_api():
    data = request.get_json() or {}
    text = data.get("text", "")
    return jsonify({
        "simplified": simplify_text(text),
        "highlighted": highlight_difficult_words(text)
    })


# =====================
# WEBSOCKET – AUTO SPEAK
# =====================
@sock.route("/ws")
def ws_handler(ws):
    print("✅ WS connected")

    # Only ever hold the single newest frame. If inference is slower
    # than the incoming frame rate, we drop old frames instead of
    # queuing them up and processing stale data.
    latest_frame = collections.deque(maxlen=1)
    stop_event = threading.Event()
    ws_lock = threading.Lock()

    def receiver():
        while not stop_event.is_set():
            try:
                data = ws.receive(timeout=1)
            except Exception:
                stop_event.set()
                break

            if data is None:
                stop_event.set()
                break

            try:
                frame = cv2.imdecode(
                    np.frombuffer(base64.b64decode(data), np.uint8),
                    cv2.IMREAD_COLOR
                )
            except Exception:
                continue

            if frame is not None:
                latest_frame.append(frame)

    recv_thread = threading.Thread(target=receiver, daemon=True)
    recv_thread.start()

    last_spoken = {}       # label -> timestamp
    SPEAK_COOLDOWN = 4     # seconds

    try:
        while not stop_event.is_set():
            if not latest_frame:
                time.sleep(0.01)
                continue

            frame = latest_frame.popleft()

            results = model(
                frame,
                conf=0.4,
                imgsz=INFER_SIZE,
                half=USE_HALF,
                verbose=False
            )

            h, w = frame.shape[:2]
            center = w // 2
            now = time.time()

            for r in results:
                for box in r.boxes:
                    try:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cls = int(box.cls[0])
                        label = model.names[cls]

                        direction = (
                            "left" if x2 < center else
                            "right" if x1 > center else
                            "ahead"
                        )
                        speak_text = f"{label} {direction}"

                        # ---- SMART SPEAK ----
                        if label not in last_spoken or now - last_spoken[label] > SPEAK_COOLDOWN:
                            try:
                                tts_q.put_nowait(speak_text)
                                last_spoken[label] = now
                            except queue.Full:
                                pass

                        # UI overlay
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                        cv2.putText(
                            frame, speak_text,
                            (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (255, 255, 0), 2
                        )
                    except Exception:
                        continue

            _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])

            try:
                with ws_lock:
                    ws.send(base64.b64encode(jpg).decode())
            except Exception:
                stop_event.set()
                break
    finally:
        stop_event.set()
        recv_thread.join(timeout=1)
        print("🔌 WS disconnected")


# =====================
# RUN
# =====================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8001,
        threaded=True,
        debug=False,
        use_reloader=False
    )