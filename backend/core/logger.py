import os
import time
import json
import threading
import cv2
import numpy as np
import uuid
from datetime import datetime
from backend.config.config import Config
from backend.core.summarizer import ClipSummarizer

class EventLogger:
    STATE_IDLE = "IDLE"
    STATE_RECORDING = "RECORDING"
    STATE_COOLDOWN = "COOLDOWN"

    def __init__(self, no_logs=False):
        self.config = Config
        self.summarizer = ClipSummarizer()
        self.no_logs = no_logs
        print(self.no_logs)
        # State
        self.state = self.STATE_IDLE
        self.active_clip_frames = [] 
        
        # Session Stats
        self.start_timestamp = 0.0
        self.trigger_level = ""
        self.current_level = ""
        self.transitions = []
        self.signal_stats = {} 
        self.weapon_seen = False
        self.max_intent = 0.0
        self.sum_intent = 0.0
        self.count_intent = 0
        
        # Timers
        self.recording_stop_time = 0.0
        self.cooldown_expiry = 0.0
        
        # Directories
        self.clips_dir = os.path.join(self.config.LOG_DIR, "clips")
        self.meta_dir = os.path.join(self.config.LOG_DIR, "metadata")
        os.makedirs(self.clips_dir, exist_ok=True)
        os.makedirs(self.meta_dir, exist_ok=True)
        
        print(f"EventLogger initialized. Fixed clip duration: {self.config.CLIP_DURATION_SECONDS}s. No Logs: {self.no_logs}")

    @property
    def is_recording(self):
        return self.state == self.STATE_RECORDING

    def update_frame(self, frame):
        """
        Process new frame.
        """
        now = time.time()
        
        if self.state == self.STATE_RECORDING:
            self.active_clip_frames.append(frame.copy())
            
            # Check Duration Expiry
            if now > self.recording_stop_time:
                self._finalize_clip()

        elif self.state == self.STATE_COOLDOWN:
            if now > self.cooldown_expiry:
                self.state = self.STATE_IDLE

    def update_state(self, threat_level, intent_score, signals, fusion_weights, weapon_present, movinet_pressure):
        """
        Check triggers and update stats.
        Note: weapon_score is now expected inside signals dict.
        """
        now = time.time()
        
        # Trigger Conditions
        if self.no_logs:
            return

        # Hard threshold >= 0.6 OR Weapon
        is_event = (intent_score >= 0.6) or weapon_present
        
        # Start Recording
        if is_event and self.state == self.STATE_IDLE:
            print(f"[LOGGER] Event Triggered: Score={intent_score:.2f}, Weapon={weapon_present}")
            self._start_recording(threat_level, intent_score, now)
            
        # Update Stats (only if recording)
        if self.state == self.STATE_RECORDING:
            self._update_stats(threat_level, intent_score, signals, weapon_present, now)

    def _start_recording(self, threat_level, intent_score, now):
        self.state = self.STATE_RECORDING
        print("[LOGGER] Recording started (Fixed 60s)")
        
        self.recording_stop_time = now + self.config.CLIP_DURATION_SECONDS
        self.active_clip_frames = [] 
        
        # Init Stats
        self.start_timestamp = now
        self.trigger_level = threat_level
        self.current_level = threat_level
        self.transitions = [] 
        self.signal_stats = {} 
        self.weapon_seen = False
        self.max_intent = 0.0
        self.sum_intent = 0.0
        self.count_intent = 0

    def _update_stats(self, threat_level, intent_score, signals, weapon_present, now):
        # 1. Transitions
        if threat_level != self.current_level:
            self.transitions.append({
                "timestamp": now,
                "rel_time": now - self.start_timestamp,
                "from": self.current_level,
                "to": threat_level
            })
            self.current_level = threat_level
            
        # 2. Weapon
        if weapon_present:
            self.weapon_seen = True
            
        # 3. Intent Stats
        self.max_intent = max(self.max_intent, intent_score)
        self.sum_intent += intent_score
        self.count_intent += 1
        
        # 4. Signal Aggregation
        for key, val in signals.items():
            if isinstance(val, (int, float)):
                if key not in self.signal_stats:
                    self.signal_stats[key] = {"sum": 0.0, "max": -float('inf'), "count": 0}
                
                s = self.signal_stats[key]
                s["sum"] += val
                s["max"] = max(s["max"], val)
                s["count"] += 1

    def _finalize_clip(self):
        print(f"[LOGGER] Finalizing clip with {len(self.active_clip_frames)} frames.")
        
        # Calculate Final Stats
        final_signals = {}
        for key, s in self.signal_stats.items():
            if key == "weapon_cooldown": continue # Skip as requested
            
            if s["count"] > 0:
                final_signals[key] = {
                    "mean": s["sum"] / s["count"],
                    "max": s["max"]
                }
        
        # Post-process Weapon Scores
        # If weapon was never confirmed (debounced), force scores to 0 to hide false positives
        if not self.weapon_seen:
             self.max_weapon_score = 0.0
             if "weapon_score" in final_signals:
                 final_signals["weapon_score"]["mean"] = 0.0
                 final_signals["weapon_score"]["max"] = 0.0

        mean_intent = self.sum_intent / self.count_intent if self.count_intent > 0 else 0.0
        
        # Construct Metadata
        metadata = {
            "clip_id": str(uuid.uuid4()),
            "timestamp": self.start_timestamp,
            "duration": self.config.CLIP_DURATION_SECONDS,
            "trigger_level": self.trigger_level, 
            "final_level": self.current_level,
            "max_intent": self.max_intent,
            "mean_intent": mean_intent,
            "weapon_detected": self.weapon_seen,
            "transitions": self.transitions,
            "signals_stats": final_signals
        }
        
        # Move to Cooldown
        self.state = self.STATE_COOLDOWN
        self.cooldown_expiry = time.time() + self.config.CLIP_COOLDOWN_SECONDS
        
        # Async Save
        frames_to_save = self.active_clip_frames
        
        # Clear active
        self.active_clip_frames = []
        self.signal_stats = {}
        self.transitions = []
        
        # Spawn thread
        t = threading.Thread(target=self._save_clip_async, args=(frames_to_save, metadata))
        t.start()

    def _save_clip_async(self, frames, metadata):
        if not frames: return
        
        # Dynamic FPS calculation: (Frames / Duration)
        # Assuming duration was strictly adhered to
        duration = metadata['duration']
        actual_fps = len(frames) / duration
        # Clamp FPS to reasonable bounds if needed, or stick to actual
        # To be safe, ensure it's not 0
        if actual_fps < 1.0: actual_fps = 1.0
        
        print(f"[LOGGER] Saving video at {actual_fps:.2f} FPS (Real-time playback).")
        
        ts_str = datetime.fromtimestamp(metadata["timestamp"]).strftime("%Y%m%d_%H%M%S")
        filename_base = f"event_{ts_str}_{metadata['final_level']}" 
        
        # Switch to WebM (VP8) for better browser compatibility without external DLLs
        vid_path = os.path.join(self.clips_dir, f"{filename_base}.webm")
        json_path = os.path.join(self.meta_dir, f"{filename_base}.json")
        
        # Write Video
        h, w, _ = frames[0].shape
        
        try:
            # VP8 is widely supported in Chrome/Edge and OpenCV
            fourcc = cv2.VideoWriter_fourcc(*'vp80')
            out = cv2.VideoWriter(vid_path, fourcc, actual_fps, (w, h))
            if not out.isOpened():
                raise Exception("vp80 failed")
        except:
             print("[LOGGER] Warning: vp80 failed, trying mp4v (might not play in browser)")
             vid_path = os.path.join(self.clips_dir, f"{filename_base}.mp4")
             fourcc = cv2.VideoWriter_fourcc(*'mp4v')
             out = cv2.VideoWriter(vid_path, fourcc, actual_fps, (w, h))

        for f in frames:
            out.write(f)
        out.release()
        
        # Write JSON
        def default_serializer(obj):
            if isinstance(obj, (np.integer, np.floating, np.bool_)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return str(obj)

        # Write Initial JSON
        def default_serializer(obj):
            if isinstance(obj, (np.integer, np.floating, np.bool_)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return str(obj)

        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=4, default=default_serializer)
            
        print(f"[LOGGER] Saved clip: {vid_path}")
        
        # Save Thumbnail (Best Frame or First Frame)
        # We can try to pick a frame with high intent if we tracked it, 
        # but for now let's just use the middle frame or the first one.
        # Ideally, we should have passed `best_frame` index or image.
        # Let's use the frame at 50% for now as a heuristic for "action".
        try:
            thumb_idx = len(frames) // 2
            thumb_frame = frames[thumb_idx]
            thumb_path = os.path.join(self.clips_dir, f"{metadata['clip_id']}.jpg")
            cv2.imwrite(thumb_path, thumb_frame)
            metadata["thumbnail_url"] = f"/videos/{metadata['clip_id']}.jpg"
            print(f"[LOGGER] Saved thumbnail: {thumb_path}")
        except Exception as e:
            print(f"[LOGGER] Failed to save thumbnail: {e}")
        
        # Generate Summary if API Key is present
        # This might take time, but we are in a thread.
        # However, if queue fills up, new events might be delayed?
        # Ideally, summarization should be a separate queue/worker if frequent.
        # For now, inline in this thread is fine as configured (60s cooldown).
        
        if self.summarizer.client:
            print("[LOGGER] Requesting AI Summary...")
            summary = self.summarizer.summarize(vid_path, metadata)
            if summary:
                metadata["summary"] = summary
                
                # Rewrite JSON with summary
                with open(json_path, 'w') as f:
                    json.dump(metadata, f, indent=4, default=default_serializer)
                print("[LOGGER] Summary saved to metadata.")
