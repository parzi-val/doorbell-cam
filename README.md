
# Doorbell Threat Detection System

A behavioral analysis system for smart doorbells that detects suspicious intent using pose estimation, motion signals, and action recognition.

## 🚀 Features

### Core Intelligence
- **Pose Estimation**: Powered by MediaPipe for real-time body tracking.
- **Signal Extraction**:
    - **Velocity & Direction**: Speed and movement vectors.
    - **Head Yaw**: Scanning behavior detection.
    - **Oscillation**: Pacing or nervous movement.
    - **Hand Fidgeting**: High-frequency hand movements.
    - **Loitering**: Detects prolonged stationary presence with subtle movements.
    - **Violence Detection**: MoViNet-based action recognition acting as a "pressure" signal.
    - **Weapon Detection**: YOLO-based weapon detection.
    - **Hysteresis & Smoothing**: Uses EMA smoothing and threshold hysteresis for stable signal processing.
- **Intent Analysis**: Fuses detection signals to classify behavior as:
    - 🟢 **CALM**
    - 🔵 **UNUSUAL**
    - 🟠 **SUSPICIOUS**
    - 🔴 **THREAT**

### Interactive Dashboard
- **Live Monitoring**: Real-time intent gauge and status updates via WebSocket.
- **Event Feed**: Auto-generated clips of detected events with "Best Frame" thumbnails.
- **Thread Alerts**: Immediate toast notifications when intent score exceeds 0.7.
- **Hardware Status**: (In Progress) Integration with physical sensors.

### The Learning System (Shadow Mode)
- **Feedback Loop**: "Accurate" / "Inaccurate" buttons for each event.
- **Credit Assignment**: Calculates which signals caused a false positive/negative.
- **Weight Updates**: Generates detailed JSON reports with proposed weight adjustments (without modifying live models).

## 🛠️ Tech Stack & Architecture

- **Backend**: Python (FastAPI, OpenCV, MediaPipe, TensorFlow Lite)
- **Frontend**: React (Vite, TailwindCSS, Recharts, Framer Motion)
- **Communication**: WebSockets for live streaming and state management.

### Directory Structure
- `backend/`: Core logic API.
    - `core/`: Signal processing (`signals.py`), intent engine (`intent.py`), pipeline (`pipeline.py`).
    - `server.py`: FastAPI entry point and WebSocket manager.
- `frontend/`: React-based dashboard.
- `logs/`: Event metadata, video clips, and learning reports.

## ⚡ Usage

### Prerequisites
- Python 3.9+
- Node.js 16+
- Webcam or Test Videos

### 1. Start Support Services
Ensure you have a `.env` file with `GEMINI_API_KEY` if using the summarizer features.

### 2. Run Backend
```bash
python backend/server.py
```
The server runs on `http://localhost:8000`.

### 3. Run Frontend
```bash
cd frontend
npm run dev
```
Access the dashboard at `http://localhost:5173`.


## 🧠 Configuration
Adjust sensitivity, thresholds, and weights in `backend/config/config.py`.

## 🔮 Future Roadmap
- **Hardware Integration**: ESP32 with PIR and Buttons (`hardware_plan.md`).
- **Face Recognition**: "Friendlies" detection using DeepFace.
