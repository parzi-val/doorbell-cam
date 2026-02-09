from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import glob
import threading
import asyncio
import time
import sys
import cv2
from typing import List, Optional

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.pipeline import Pipeline
from backend.config.config import Config

# Disable internal threading to prevent GIL issues
cv2.setNumThreads(0)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
CLIPS_DIR = os.path.join(LOG_DIR, "clips")
META_DIR = os.path.join(LOG_DIR, "metadata")
DASHBOARD_DIR = os.path.join(BASE_DIR, "frontend")

# ... (ConnectionManager same)
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.sensor_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def connect_sensor(self, websocket: WebSocket):
        await websocket.accept()
        self.sensor_connections.append(websocket)
        print("Sensor connected!")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.sensor_connections:
            self.sensor_connections.remove(websocket)

    async def broadcast_bytes(self, data: bytes):
        for connection in self.active_connections:
            try:
                await connection.send_bytes(data)
            except Exception:
                pass

    async def broadcast_json(self, data: dict):
        # Only send high-bandwidth data to frontend clients
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                pass

manager = ConnectionManager()

# Global State
pipeline = None
pipeline_thread = None
latest_frame_data = None # (jpg_bytes, metadata)
data_lock = threading.Lock()
running = False
frame_counter = 0

def frame_handler(jpg_bytes, metadata):
    """
    Callback from Pipeline thread.
    Updates the latest frame data.
    """
    global latest_frame_data, frame_counter
    
    with data_lock:
        latest_frame_data = (jpg_bytes, metadata)
    
    frame_counter += 1
    if frame_counter % 100 == 0:
        print(f"[SERVER] Processing frame {frame_counter}, JPG Size: {len(jpg_bytes)} bytes")

broadcast_active = False

async def broadcast_loop():
    """
    Async loop to push updates to websockets.
    """
    global latest_frame_data, broadcast_active
    
    while broadcast_active:
        data_to_send = None
        
        with data_lock:
            if latest_frame_data:
                data_to_send = latest_frame_data
                latest_frame_data = None
        
        if data_to_send:
            jpg, meta = data_to_send
            # Send Metadata first (text)
            await manager.broadcast_json(meta)
            # Send Frame (binary)
            await manager.broadcast_bytes(jpg)
            
        await asyncio.sleep(0.015) # ~60 FPS check rate

@app.on_event("startup")
def startup_event():
    global pipeline, pipeline_thread, running, broadcast_active
    print("Starting Pipeline in background...")
    running = True
    broadcast_active = True
    
    # Initialize Pipeline
    pipeline = Pipeline(headless=True, no_logs=Config.NO_LOGS)
    
    # Start Thread
    def run_pipeline():
        pipeline.run(headless=True, frame_callback=frame_handler)
        
    pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
    pipeline_thread.start()
    
    # Start Broadcast Loop
    asyncio.create_task(broadcast_loop())





@app.on_event("shutdown")
def shutdown_event():
    # This is called by Uvicorn on nice shutdown.
    # We can try to be nice first.
    global running, pipeline, broadcast_active
    print("Stopping Pipeline...")
    running = False
    broadcast_active = False
    if pipeline:
        pipeline.stop()
    if pipeline_thread:
        # Don't join forever, just wait a bit then let the main process exit kill it
        pipeline_thread.join(timeout=1.0)
    print("Pipeline stopped.")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive / receive frontend commands
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        pass

@app.websocket("/ws/sensor")
async def sensor_websocket_endpoint(websocket: WebSocket):
    global pipeline
    await manager.connect_sensor(websocket)
    try:
        while True:
            # Handle sensor data from ESP
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                
                # Hardware Action: Doorbell Press
                if msg.get("type") == "sensor_reading" and msg.get("sensor") == "doorbell_btn" and msg.get("state") == "pressed":
                    if pipeline:
                         pipeline.trigger_doorbell()

                # Broadcast relevant sensor events to Frontends
                if msg.get("type") in ["sensor_reading", "heartbeat"]:
                    await manager.broadcast_json(msg)
            except:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        pass


@app.get("/api/events")
def get_events():
    events = []
    # glob all json in metadata
    pattern = os.path.join(META_DIR, "*.json")
    files = glob.glob(pattern)
    
    # Sort by time (filename usually has timestamp or check content)
    # Filename: event_YYYYMMDD_HHMMSS_LEVEL.json
    files.sort(key=os.path.getmtime, reverse=True)
    
    for f in files:
        try:
            with open(f, 'r') as json_file:
                data = json.load(json_file)
                # Add filename for reference
                filename = os.path.basename(f)
                
                video_url = None
                
                # Method 1: Check by clip_id (UUID)
                if "clip_id" in data:
                    cid = data["clip_id"]
                    if os.path.exists(os.path.join(CLIPS_DIR, f"{cid}.mp4")):
                        video_url = f"/videos/{cid}.mp4"
                    elif os.path.exists(os.path.join(CLIPS_DIR, f"{cid}.webm")):
                        video_url = f"/videos/{cid}.webm"
                        
                # Method 2: Check by filename (Legacy/Fallback)
                if not video_url:
                    webm_name = filename.replace(".json", ".webm")
                    mp4_name = filename.replace(".json", ".mp4")
                    
                    if os.path.exists(os.path.join(CLIPS_DIR, webm_name)):
                         video_url = f"/videos/{webm_name}"
                    elif os.path.exists(os.path.join(CLIPS_DIR, mp4_name)):
                         video_url = f"/videos/{mp4_name}"
                
                if video_url:
                     data["video_url"] = video_url
                     # Check for thumbnail
                     if "clip_id" in data:
                         thumb_path = os.path.join(CLIPS_DIR, f"{data['clip_id']}.jpg")
                         if os.path.exists(thumb_path):
                             data["thumbnail_url"] = f"/videos/{data['clip_id']}.jpg"
                     
                     data["meta_filename"] = filename
                     events.append(data)
                elif "clip_id" in data: 
                    # Even if video missing, return event if we have data? 
                    # Frontend might break if no video_url. Let's skip for consistency with valid events only.
                    # Or provide null?
                    # The original logic skipped. Stick to skipping or maybe log warning.
                    pass

        except Exception as e:
            print(f"Error loading {f}: {e}")
            
    return events

# Mounts for static serving
# Must be after API routes to avoid intercepting them
app.mount("/videos", StaticFiles(directory=CLIPS_DIR), name="videos")

# --- Test / Replay Endpoints ---
TEST_CLIPS_DIR = os.path.join(BASE_DIR, "test-videos", "output")
TEST_DATA_DIR = os.path.join(BASE_DIR, "test-videos", "data02")

class TestStartRequest(BaseModel):
    filename: str

@app.get("/api/test/videos")
def list_test_videos():
    # List supported video files
    extensions = ['*.mp4', '*.webm', '*.avi', '*.mov']
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(TEST_CLIPS_DIR, ext)))
    
    return [os.path.basename(f) for f in files]

replay_running = False

def run_replay(filename):
    global replay_running, latest_frame_data
    
    print(f"[REPLAY] Starting replay for {filename}")
    
    video_path = os.path.join(TEST_CLIPS_DIR, filename)
    json_path = os.path.join(TEST_DATA_DIR, os.path.splitext(filename)[0] + ".json")
    
    if not os.path.exists(json_path):
        print(f"[REPLAY] Error: JSON data not found for {filename}")
        return

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        frames_data = data.get("frames", [])
        fps = data.get("fps", 30.0)
        dt = 1.0 / fps
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[REPLAY] Error: Could not open video {filename}")
            return
            
        print(f"[REPLAY] Loaded {len(frames_data)} frames from JSON. FPS: {fps}")
        
        frame_idx = 0
        total_frames = len(frames_data)
        
        while replay_running and cap.isOpened():
            start_time = time.time()
            
            ret, frame = cap.read()
            if not ret:
                print("[REPLAY] Video ended. Stopping.")
                replay_running = False
                break
            
            if frame_idx % 100 == 0:
                 print(f"[REPLAY] Frame {frame_idx}/{total_frames}")

            # Get pre-computed metadata
            meta = {}
            if frame_idx < total_frames:
                meta = frames_data[frame_idx]
            else:
                 # Should not happen if synced, but fallback
                 meta = frames_data[-1] if frames_data else {}
            
            # Encode Frame
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            if ret:
                jpg_bytes = buffer.tobytes()
                
                # Update global latest_frame_data for the broadcast_loop to pick up
                # Note: broadcast_loop sends whatever is in latest_frame_data
                with data_lock:
                    latest_frame_data = (jpg_bytes, meta)
            
            frame_idx += 1
            
            # Throttle
            elapsed = time.time() - start_time
            wait = dt - elapsed
            if wait > 0:
                time.sleep(wait)
                
        cap.release()
        print("[REPLAY] Stopped.")
        
    except Exception as e:
        print(f"[REPLAY] Error: {e}")
        import traceback
        traceback.print_exc()

@app.post("/api/test/start")
def start_simulation(request: TestStartRequest):
    global pipeline, pipeline_thread, running, replay_running
    
    filename = request.filename
    
    print(f"[SERVER] Starting REPLAY mode with: {filename}")
    
    # 1. Stop Pipeline (Webcam)
    # We keep broadcast_active = True
    if running:
        print("[SERVER] Stopping Webcam Pipeline...")
        running = False
        if pipeline:
            pipeline.stop()
        if pipeline_thread:
            pipeline_thread.join()
    
    # 2. Stop existing Replay if any
    if replay_running:
         replay_running = False
         # Wait a bit? Ideally we track the thread.
         time.sleep(0.5)

    # 3. Start Replay Thread
    replay_running = True
    
    # We use a separate thread for replay generation, 
    # but we reuse the SAME broadcast_loop (it reads latest_frame_data).
    # So run_replay just needs to update latest_frame_data.
    
    replay_thread = threading.Thread(target=run_replay, args=(filename,), daemon=True)
    replay_thread.start()
    
    return {"status": "started", "mode": "replay", "file": filename}

@app.post("/api/test/stop")
def stop_simulation():
    global replay_running
    
    print(f"[SERVER] Stopping REPLAY.")
    replay_running = False
    # Do NOT restart webcam automatically.
    
    return {"status": "stopped", "source": "none"}

@app.post("/api/live/start")
def start_live_feed():
    global pipeline, pipeline_thread, running, replay_running
    
    print(f"[SERVER] Switching to LIVE Webcam.")
    
    # 1. Stop Replay if running
    if replay_running:
        replay_running = False
        time.sleep(0.5)
        
    # 2. Start Webcam Pipeline if not running
    if not running:
        running = True
        pipeline = Pipeline(headless=True, no_logs=Config.NO_LOGS)
        
        def run_pipeline():
            pipeline.run(input_source=0, headless=True, frame_callback=frame_handler)
            
        pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
        pipeline_thread.start()
        return {"status": "started", "source": "webcam"}
    else:
        return {"status": "already_running", "source": "webcam"}

class FeedbackRequest(BaseModel):
    event_id: str
    feedback_type: str # "accurate" or "inaccurate"

@app.post("/api/feedback")
def submit_feedback(request: FeedbackRequest):
    from backend.core.learning import LearningSystem
    ls = LearningSystem()
    report = ls.process_feedback(request.event_id, request.feedback_type)
    return report

if __name__ == "__main__":
    import uvicorn
    # If running directly, startup event fires automatically
    uvicorn.run(app, host="0.0.0.0", port=8000)
