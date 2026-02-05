
import cv2
import time
import numpy as np
import mediapipe as mp
from backend.config.config import Config
from backend.core.pose_detector import PoseDetector
from backend.core.signals import SignalProcessor
from backend.core.visualization import Visualizer
from backend.core.intent import IntentEngine
from backend.core.violence import ViolenceWorker
from backend.core.weapon import WeaponWorker

class Pipeline:
    def __init__(self):
        self.config = Config()
        
        # Components
        self.detector = PoseDetector()
        self.processor = SignalProcessor()
        self.intent_engine = IntentEngine()
        self.visualizer = Visualizer()
        
        # Threaded Workers
        self.violence_worker = ViolenceWorker()
        self.violence_worker.start()
        
        self.weapon_worker = WeaponWorker()
        self.weapon_worker.start()

    def run(self):
        print("Starting pipeline... Press ESC to exit.")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Could not open webcam")
            return
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            # Send frame to workers
            self.violence_worker.process_frame(frame)
            self.weapon_worker.process_frame(frame)
            
            # Get latest results
            movinet_probs = self.violence_worker.get_latest_probability()
            weapon_detections = self.weapon_worker.get_latest_detections()

            # Detect Pose
            t_ms = int(time.time() * 1000)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.detector.detect(mp_image, t_ms)

            # Process Signals
            current_clock_time = time.time()
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
            self.visualizer.draw_overlay(frame, signals, intent_score, threat_level, weapon_detections)
            self.visualizer.update_plots(self.processor.get_buffers()) # Could pass intent history too if we buffer it
            self.visualizer.show_frame(frame)

            if cv2.waitKey(1) & 0xFF == 27: # ESC
                break

        self.close()
        cap.release() # Release the local cap object

    def close(self):
        # self.cap.release() # Handled in run()
        self.detector.close()
        self.visualizer.close()
