# 🧠 Crowd Vision — ML-Driven Crowd Detection & Analysis System

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat-square&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat-square&logo=streamlit)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?style=flat-square)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

A real-time crowd detection and analysis system that uses **YOLOv8** object detection, **FastAPI** as the backend, and **Streamlit** as the frontend dashboard. Upload any video and get instant crowd metrics, risk evaluation, and session logs stored in MongoDB Atlas.

---

## 📸 Features

- 🎯 **YOLOv8-powered person detection** with multi-object tracking across frames
- 📊 **Real-time crowd metrics** — total people seen, peak live count, crowd index, average proximity
- 🚨 **Risk level evaluation** — LOW / MEDIUM / HIGH based on crowd density
- 🎥 **Annotated video output** — processed video with red dot markers on detected persons
- 🗄️ **MongoDB Atlas logging** — every session stored with frame-level stats and crowd periods
- 📈 **Interactive Streamlit dashboard** with Plotly charts and a risk gauge
- 💾 **CSV report download** after each analysis
- 🌐 **REST API** via FastAPI for integration with other systems

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   User / Browser                    │
└──────────────────────┬──────────────────────────────┘
                       │  Upload .mp4
                       ▼
┌─────────────────────────────────────────────────────┐
│            Streamlit Frontend  (app.py)             │
│   Dashboard │ Charts │ Risk Gauge │ CSV Download    │
└──────────────────────┬──────────────────────────────┘
                       │  POST /analyze/
                       ▼
┌─────────────────────────────────────────────────────┐
│            FastAPI Backend  (MAIN2.py)              │
│                                                     │
│  ┌─────────────┐     ┌──────────────────────────┐  │
│  │  YOLOv8n    │────▶│   analyze_video()        │  │
│  │  Tracker    │     │   - Person detection     │  │
│  └─────────────┘     │   - Proximity calc       │  │
│                      │   - Crowd event logging  │  │
│                      │   - Annotated video out  │  │
│                      └────────────┬─────────────┘  │
└───────────────────────────────────┼────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │      MongoDB Atlas        │
                    │  sessions collection      │
                    │  - frame_stats[]          │
                    │  - crowd_periods[]        │
                    │  - crowd_index, ratio     │
                    └───────────────────────────┘
```

---

## 📂 Project Structure

```
Crowd-Detection/
│
├── MAIN2.py               # FastAPI backend — video analysis + MongoDB logging
├── main.py                # FastAPI backend — lightweight version (Excel logging)
├── app.py                 # Streamlit frontend dashboard
├── vehicles.py            # Vehicle tracking utility class
├── a.py                   # Quick test/utility script
│
├── statics/
│   ├── script.js          # Frontend JS for HTML interface
│   └── style.css          # Styles for HTML interface
│
├── templates/
│   └── index.html         # Alternate HTML frontend
│
├── outputs/               # Auto-generated processed videos (git-ignored)
├── uploads/               # Temp upload directory (git-ignored)
│
├── .env                   # Environment variables — NOT committed
├── .gitignore
└── README.md
```

---

## ⚙️ How It Works

### 1. Video Upload
The user uploads an `.mp4` file through the Streamlit UI. It is sent via HTTP POST to the FastAPI `/analyze/` endpoint.

### 2. Frame-by-Frame Analysis
Each frame is processed by **YOLOv8n** with persistent tracking (class 0 = person only):
- Detected person centers are extracted
- Pairwise distances between all persons are computed
- A **crowd event** is triggered when:
  - `live_count >= 8` (PEOPLE_THRESHOLD)
  - `avg_proximity <= 150px` (PROXIMITY_THRESHOLD)

### 3. Crowd Index Calculation
```
Crowd Index = (Peak Live Count × 0.5) + (Total Crowd Duration × 0.3) + (Crowd Events × 0.2)
```

| Crowd Index | Risk Level |
|-------------|------------|
| 0 – 8       | 🟢 LOW     |
| 8 – 15      | 🟡 MEDIUM  |
| 15+         | 🔴 HIGH    |

### 4. Output
- Annotated video saved to `outputs/` with red dots on each detected person
- Full session document saved to MongoDB Atlas
- JSON response returned to Streamlit for dashboard rendering

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- MongoDB Atlas account (free tier works)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> If you don't have a `requirements.txt` yet, install manually:
> ```bash
> pip install fastapi uvicorn streamlit ultralytics opencv-python numpy pandas pymongo certifi plotly openpyxl python-multipart
> ```

### 3. Set up environment variables

Create a `.env` file in the project root:

```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/sample_mflix?retryWrites=true&w=majority&appName=crowd
```

Replace `<username>`, `<password>`, and `<cluster>` with your MongoDB Atlas credentials.

### 4. Download YOLOv8 model

The model downloads automatically on first run via `ultralytics`. To pre-download:

```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### 5. Run the FastAPI backend

```bash
uvicorn MAIN2:app --reload --port 8000
```

### 6. Run the Streamlit frontend

Open a second terminal:

```bash
streamlit run app.py
```

Then open your browser at `http://localhost:8501`

---

## 🖥️ Usage

1. Open the Streamlit dashboard at `http://localhost:8501`
2. Click **"Choose an .mp4 file"** and upload your video
3. Wait for analysis to complete (time depends on video length)
4. View the results:
   - **Metrics panel** — 8 crowd statistics
   - **Charts** — People count, behavior metrics, duration, proximity
   - **Risk gauge** — Visual crowd index indicator
   - **Report table** — Full summary
5. Click **"Download CSV"** to save the report

---

## 📡 API Reference

### `POST /analyze/`

Upload a video for analysis.

**Request:** `multipart/form-data`
| Field | Type | Description |
|-------|------|-------------|
| `file` | `.mp4` | Video file to analyze |

**Response:** `application/json`
```json
{
  "id": "session_mongo_id",
  "video_name": "crowd_test.mp4",
  "session_id": "2026-06-05T10:30:00",
  "fps": 30.0,
  "resolution": { "width": 1280, "height": 720 },
  "total_frames": 900,
  "peak_live_count": 12,
  "total_people_seen": 27,
  "avg_proximity_session": 134.5,
  "total_crowd_duration": 18.3,
  "crowd_events": 3,
  "crowd_index": 11.49,
  "crowd_ratio": 0.61,
  "video_path": "outputs/processed_crowd_test.mp4"
}
```

### `GET /video/{filename}`

Stream a processed output video.

---

## 🗄️ MongoDB Schema

Each analysis session creates one document in the `sessions` collection:

```json
{
  "_id": "ObjectId",
  "video_name": "string",
  "session_id": "ISO timestamp",
  "started_at": "datetime",
  "finished_at": "datetime",
  "fps": "float",
  "resolution": { "width": "int", "height": "int" },
  "total_frames": "int",
  "peak_live_count": "int",
  "total_people_seen": "int",
  "avg_proximity_session": "float",
  "total_crowd_duration": "float",
  "crowd_events": "int",
  "crowd_index": "float",
  "crowd_ratio": "float",
  "crowd_periods": [
    { "start": "datetime", "end": "datetime", "duration": "float" }
  ],
  "frame_stats": [
    { "frame_no": "int", "live_count": "int", "avg_proximity": "float", "ts": "datetime" }
  ],
  "final": "bool"
}
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Object Detection | [YOLOv8](https://github.com/ultralytics/ultralytics) (ultralytics) |
| Backend API | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Frontend Dashboard | [Streamlit](https://streamlit.io/) |
| Video Processing | [OpenCV](https://opencv.org/) |
| Database | [MongoDB Atlas](https://www.mongodb.com/atlas) |
| Charts | [Plotly](https://plotly.com/) |
| Numerical Computing | NumPy, Pandas |

---

## 🔒 Environment & Security

- MongoDB credentials are loaded via `os.environ.get("MONGO_URI")` — never hardcoded
- `.env` file is git-ignored
- Model weights (`.pt`) and video files (`.mp4`) are git-ignored due to size

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 👥 About

Built by **Crowd Vision** — a tech initiative focused on real-time crowd analytics using Machine Learning and Computer Vision for safer, smarter public spaces.

> 📧 contact@crowdvision.tech | 🌐 www.crowdvision.tech | 📍 Pune, Maharashtra, India