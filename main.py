from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from datetime import datetime
from ultralytics import YOLO
import numpy as np
import pandas as pd
import cv2
import os
import math
import shutil
from tempfile import NamedTemporaryFile

app = FastAPI()

# Load YOLOv8 model once at startup
model = YOLO("yolov8n.pt")

def analyze_video(video_path: str, excel_path: str = "crowd_log.xlsx") -> dict:
    cap = cv2.VideoCapture(video_path)
    unique_ids = set()
    peak_people_count = 0
    crowd_start_time = None
    crowd_durations = []
    crowd_trigger_count = 0
    proximity_accumulator = []
    frame_count = 0

    PEOPLE_THRESHOLD = 8
    PROXIMITY_THRESHOLD = 150
    session_start = datetime.now()
    session_id = session_start.strftime("%Y-%m-%d %H:%M:%S")
    video_name = os.path.basename(video_path)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        results = model.track(frame, persist=True, classes=[0])

        ids = results[0].boxes.id.cpu().numpy().astype(int) if results[0].boxes.id is not None else []
        boxes = results[0].boxes.xywh.cpu().numpy() if results[0].boxes is not None else []

        people = []
        for idx, box in enumerate(boxes):
            x, y, w, h = box
            center_x, center_y = int(x), int(y)
            people.append((center_x, center_y))
            if idx < len(ids):
                unique_ids.add(ids[idx])

        live_count = len(people)
        peak_people_count = max(peak_people_count, live_count)

        distances = [
            math.hypot(people[i][0] - people[j][0], people[i][1] - people[j][1])
            for i in range(len(people)) for j in range(i + 1, len(people))
        ]
        avg_proximity = np.mean(distances) if distances else 0
        proximity_accumulator.append(avg_proximity)

        if live_count >= PEOPLE_THRESHOLD and avg_proximity <= PROXIMITY_THRESHOLD:
            if crowd_start_time is None:
                crowd_start_time = datetime.now()
                crowd_trigger_count += 1
        else:
            if crowd_start_time:
                duration = (datetime.now() - crowd_start_time).total_seconds()
                crowd_durations.append(duration)
                crowd_start_time = None

    if crowd_start_time:
        duration = (datetime.now() - crowd_start_time).total_seconds()
        crowd_durations.append(duration)

    total_people_seen = len(unique_ids)
    avg_proximity_session = np.mean(proximity_accumulator) if proximity_accumulator else 0
    crowd_duration_total = sum(crowd_durations)
    crowd_index = (peak_people_count * 0.5 + crowd_duration_total * 0.3 + crowd_trigger_count * 0.2)

    result = {
        "Timestamp": session_id,
        "Video": video_name,
        "Total People Seen": total_people_seen,
        "Max Live Count": peak_people_count,
        "Crowd Duration (sec)": crowd_duration_total,
        "Avg Proximity": avg_proximity_session,
        "Crowd Events": crowd_trigger_count,
        "Crowd Index": crowd_index
    }

    # Save to Excel
    df = pd.DataFrame([result])
    if os.path.exists(excel_path):
        existing_df = pd.read_excel(excel_path, sheet_name="Log")
        combined_df = pd.concat([existing_df, df], ignore_index=True)
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
            combined_df.to_excel(writer, sheet_name="Log", index=False)
    else:
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="Log", index=False)

    cap.release()
    return result

@app.post("/analyze/")
async def upload_video(file: UploadFile = File(...)):
    # Save uploaded file temporarily
    with NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = analyze_video(tmp_path)
        return JSONResponse(content=result)
    finally:
        os.remove(tmp_path)
        

