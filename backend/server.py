from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import glob
from typing import List, Optional

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
CLIPS_DIR = os.path.join(LOG_DIR, "clips")
META_DIR = os.path.join(LOG_DIR, "metadata")
DASHBOARD_DIR = os.path.join(BASE_DIR, "frontend")


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
                video_filename = filename.replace(".json", ".mp4")
                
                # Check if video exists
                if os.path.exists(os.path.join(CLIPS_DIR, video_filename)):
                    data["video_url"] = f"/videos/{video_filename}"
                    data["meta_filename"] = filename
                    events.append(data)
        except Exception as e:
            print(f"Error loading {f}: {e}")
            
    return events

# Mounts for static serving
# Must be after API routes to avoid intercepting them
app.mount("/videos", StaticFiles(directory=CLIPS_DIR), name="videos")
app.mount("/", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
