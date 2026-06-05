from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from ultralytics import YOLO
import numpy as np
import cv2
import os
import math
import shutil
from tempfile import NamedTemporaryFile
from pymongo import MongoClient
import certifi
import time

# Constants
PEOPLE_THRESHOLD = 8
PROXIMITY_THRESHOLD = 150
OUTPUT_DIR = "outputs"
MODEL_PATH = "yolov8n.pt"

# MongoDB setup
MONGO_URI = (
    "mongodb+srv://harsh:hT6jMhF2ZKJ64GW2"
    "@crowd.wy6e3yo.mongodb.net/sample_mflix"
    "?retryWrites=true&w=majority&appName=crowd"
)
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["sample_mflix"]
sessions = db["sessions"]

# FastAPI app setup
app = FastAPI()
model = YOLO(MODEL_PATH)

# Serve processed videos from the /video route
app.mount("/video", StaticFiles(directory=OUTPUT_DIR), name="video")


def analyze_video(video_path: str) -> dict:
    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 1
        total_fr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_filename = f"processed_{os.path.basename(video_path)}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_vid = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        start_ts = datetime.utcnow()
        doc = {
            "video_name": os.path.basename(video_path),
            "session_id": start_ts.isoformat(),
            "started_at": start_ts,
            "fps": fps,
            "resolution": {"width": width, "height": height},
            "total_frames": total_fr,
            "peak_live_count": 0,
            "crowd_periods": [],
            "frame_stats": [],
            "final": False
        }

        res = sessions.insert_one(doc)
        sess_id = res.inserted_id
        unique_ids = set()
        crowd_start = None
        prox_hist = []
        frame_no = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_no += 1

            out = model.track(frame, persist=True, classes=[0])[0]
            ids = [] if out.boxes.id is None else out.boxes.id.cpu().numpy().astype(int).tolist()
            boxes = [] if out.boxes.xywh is None else out.boxes.xywh.cpu().numpy().tolist()

            unique_ids.update(ids)
            centers = [(int(x), int(y)) for x, y, _, _ in boxes]
            live_count = len(centers)

            if live_count > doc["peak_live_count"]:
                sessions.update_one({"_id": sess_id}, {"$set": {"peak_live_count": live_count}})

            dists = [
                math.hypot(centers[i][0] - centers[j][0], centers[i][1] - centers[j][1])
                for i in range(len(centers)) for j in range(i + 1, len(centers))
            ]
            avg_prox = float(np.mean(dists)) if dists else 0.0
            prox_hist.append(avg_prox)

            if live_count >= PEOPLE_THRESHOLD and avg_prox <= PROXIMITY_THRESHOLD:
                if crowd_start is None:
                    crowd_start = datetime.utcnow()
            else:
                if crowd_start is not None:
                    end_ts = datetime.utcnow()
                    dur = (end_ts - crowd_start).total_seconds()
                    sessions.update_one({"_id": sess_id}, {"$push": {"crowd_periods": {
                        "start": crowd_start, "end": end_ts, "duration": dur}}})
                    crowd_start = None

            if frame_no % 3 == 0 or frame_no == total_fr:
                snap = {
                    "frame_no": frame_no,
                    "live_count": live_count,
                    "avg_proximity": avg_prox,
                    "ts": datetime.utcnow()
                }
                sessions.update_one({"_id": sess_id}, {"$push": {"frame_stats": snap}})

            # Draw red dots on people
            for center in centers:
                cv2.circle(frame, center, 5, (0, 0, 255), -1)

            out_vid.write(frame)

        if crowd_start is not None:
            end_ts = datetime.utcnow()
            dur = (end_ts - crowd_start).total_seconds()
            sessions.update_one({"_id": sess_id}, {"$push": {"crowd_periods": {
                "start": crowd_start, "end": end_ts, "duration": dur}}})

        out_vid.release()
        cap.release()

        total_seen = len(unique_ids)
        avg_prox_sess = float(np.mean(prox_hist)) if prox_hist else 0.0
        sess_doc = sessions.find_one({"_id": sess_id})
        tot_crowd_time = sum(p["duration"] for p in sess_doc["crowd_periods"])
        crowd_events = len(sess_doc["crowd_periods"])
        crowd_ratio = tot_crowd_time / (total_fr / fps) if total_fr > 0 else 0
        crowd_index = sess_doc["peak_live_count"] * 0.5 + tot_crowd_time * 0.3 + crowd_events * 0.2

        sessions.update_one({"_id": sess_id}, {"$set": {
            "unique_ids": list(unique_ids),
            "total_people_seen": total_seen,
            "avg_proximity_session": avg_prox_sess,
            "total_crowd_duration": tot_crowd_time,
            "crowd_events": crowd_events,
            "crowd_index": crowd_index,
            "crowd_ratio": crowd_ratio,  # ✅ Add this line
            "finished_at": datetime.utcnow(),
            "final": True
        }})


        # Final session doc with updated stats
        sess_doc = sessions.find_one({"_id": sess_id})
        return {**sess_doc, "video_path": output_path}
    finally:
        cap.release()


@app.post("/analyze/")
async def upload_video(file: UploadFile = File(...)):
    with NamedTemporaryFile(delete=False, suffix=".mp4", dir="/tmp") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        doc = analyze_video(tmp_path)
        if "error" in doc:
            return JSONResponse(status_code=500, content=doc)
        doc["id"] = str(doc.pop("_id"))
        return JSONResponse(content=doc)
    finally:
        time.sleep(1)  # Ensure file cleanup on some OS


@app.get("/video/{filename}")
def get_video(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4")
    return JSONResponse(content={"error": "File not found"}, status_code=404)
