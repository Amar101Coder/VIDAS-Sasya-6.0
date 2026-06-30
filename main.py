import base64
import time
import threading
import queue
import cv2
import numpy as np

from flask import Flask, render_template, request, jsonify, send_from_directory
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
# YOLO
# =====================
model = YOLO("yolov8n.pt")
try:
    model.to("cuda")
except:
    print("⚠️ CPU mode")

model.fuse()

# =====================
# OFFLINE TTS (pyttsx3)
# =====================
tts_q = queue.Queue(maxsize=10)

engine = pyttsx3.init()
engine.setProperty("rate", 145)
engine.setProperty("volume", 1.0)

def tts_worker():
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

    last_infer = 0
    last_spoken = {}   # label -> timestamp
    SPEAK_COOLDOWN = 4  # seconds

    while True:
        data = ws.receive()
        if data is None:
            break

        try:
            frame = cv2.imdecode(
                np.frombuffer(base64.b64decode(data), np.uint8),
                cv2.IMREAD_COLOR
            )
        except:
            continue

        if frame is None:
            continue

        if time.time() - last_infer < 0.2:
            continue
        last_infer = time.time()

        results = model(frame, conf=0.4, verbose=False)

        h, w = frame.shape[:2]
        center = w // 2

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
                    now = time.time()
                    if label not in last_spoken or now - last_spoken[label] > SPEAK_COOLDOWN:
                        try:
                            tts_q.put_nowait(speak_text)
                            last_spoken[label] = now
                        except queue.Full:
                            pass

                    # UI overlay
                    cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,255), 2)
                    cv2.putText(
                        frame, speak_text,
                        (x1, max(20,y1-10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (255,255,0), 2
                    )
                except:
                    continue

        _, jpg = cv2.imencode(".jpg", frame)
        ws.send(base64.b64encode(jpg).decode())

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
