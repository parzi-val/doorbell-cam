
import cv2
import time
import numpy as np
import mediapipe as mp
from backend.config.config import Config, IntentConfig
from backend.core.pose_detector import PoseDetector
from backend.core.signals import SignalProcessor
from backend.core.visualization import Visualizer
from backend.core.intent import IntentEngine
from backend.core.violence import ViolenceWorker
from backend.core.weapon import WeaponWorker
from backend.core.logger import EventLogger

class Pipeline:
    def __init__(self, headless=False, no_logs=False):
        self.config = Config()
        
        # Components
        self.detector = PoseDetector()
        self.processor = SignalProcessor()
        self.intent_engine = IntentEngine()
        self.visualizer = Visualizer(headless=headless)
        self.logger = EventLogger(no_logs=no_logs)
        
        # Threaded Workers
        self.violence_worker = ViolenceWorker()
        self.violence_worker.start()
        
        self.weapon_worker = WeaponWorker()
        self.weapon_worker.start()
        
    def reset(self):
        """Reset pipeline state."""
        # Re-instantiate logic components to ensure clean state
        self.processor = SignalProcessor()
        self.intent_engine = IntentEngine()
        
        # Reset detectors and workers
        self.detector.reset()
        self.violence_worker.reset()
        self.weapon_worker.reset()

    def trigger_doorbell(self):
        """Pass hardware trigger to processor."""
        if hasattr(self, 'processor'):
            self.processor.trigger_doorbell()

    def run(self, input_source=0, headless=False, frame_callback=None, throttle=True):
        print(f"Starting pipeline on source: {input_source}")

        if not headless:
            print("Press ESC to exit local window.")
            
        cap = cv2.VideoCapture(input_source)
        if not cap.isOpened():
            print(f"Could not open source: {input_source}")
            return
        
        # Init placeholders for holding previous values
        movinet_probs = np.array([0.0, 0.0])
        weapon_detections = []

        self.running = True
        
        # Simulated time for fast processing
        sim_time = time.time()

        while cap.isOpened() and self.running:
            ret, frame = cap.read()
            if not ret: break
            
            # Determine Time
            if isinstance(input_source, str) and not throttle:
                # Fast processing: Advance time by fixed DT
                sim_time += self.config.DT
                current_clock_time = sim_time
            else:
                # Real-time / Throttled
                current_clock_time = time.time()

            # Send frame to workers
            if self.violence_worker.is_alive():
                 self.violence_worker.process_frame(frame)
            if self.weapon_worker.is_alive():
                 self.weapon_worker.process_frame(frame)
            
            # Get latest results
            # Violence
            prob = self.violence_worker.get_latest_probability()
            if prob is not None:
                 movinet_probs = prob
            
            # Weapon
            dets = self.weapon_worker.get_latest_detections()
            if dets is not None:
                 weapon_detections = dets

            # Detect Pose
            t_ms = int(current_clock_time * 1000)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.detector.detect(mp_image, t_ms)

            # Process Signals
            if result.pose_landmarks:
                lm = result.pose_landmarks[0]
                lm_xy = np.array([(l.x, l.y) for l in lm])
                self.processor.update(lm_xy, current_clock_time, movinet_probs, weapon_detections)
            else:
                self.processor.update_empty(movinet_probs, weapon_detections)

            # Compute Signals
            signals = self.processor.compute_signals(current_clock_time)
            
            # Intent Analysis
            intent_score, threat_level, _ = self.intent_engine.update(signals)

            # Visualization
            if not headless:
                self.visualizer.draw_overlay(frame, signals, intent_score, threat_level, weapon_detections, is_recording=self.logger.is_recording)
                self.visualizer.update_plots(self.processor.get_buffers()) 
                self.visualizer.show_frame(frame)
            
            # Logging Hook
            self.logger.update_frame(frame)
            
            # Calculate max weapon score
            max_weapon_conf = 0.0
            if weapon_detections:
                 max_weapon_conf = max(d['score'] for d in weapon_detections)

            # Add max weapon score to signals for auto-aggregation in logger
            signals["weapon_score"] = max_weapon_conf
            
            self.logger.update_state(
                threat_level=threat_level,
                intent_score=intent_score,
                signals=signals,
                fusion_weights=IntentConfig.WEIGHTS,
                weapon_present=signals.get("weapon_confirmed", False),
                movinet_pressure=signals.get("movinet_pressure", 0.0)
            )

            # Callback for Streaming
            if frame_callback:
                # Encode frame to JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                if ret:
                    jpg_bytes = buffer.tobytes()
                    # Metadata payload
                    metadata = {
                        "intent_score": float(intent_score),
                        "threat_level": threat_level,
                        "signals": {k: float(v) for k, v in signals.items() if isinstance(v, (int, float))}
                    }
                    frame_callback(jpg_bytes, metadata)

            if not headless:
                if cv2.waitKey(1) & 0xFF == 27: # ESC
                    break
            
            # Throttle for simulation (file input)
            if isinstance(input_source, str) and throttle:
                # Simple sleep to match FPS
                time.sleep(self.config.DT)

        self.close()
        cap.release()

    def stop(self):
        self.running = False
            
    def close(self):
        self.detector.close()
        self.visualizer.close()
