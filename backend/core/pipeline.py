
import cv2
import time
import numpy as np
import mediapipe as mp
from backend.config.config import Config
from backend.core.pose_detector import PoseDetector
from backend.core.signals import SignalProcessor
from backend.core.visualization import Visualizer
from backend.core.intent import IntentEngine

class Pipeline:
    def __init__(self):
        self.config = Config
        self.detector = PoseDetector()
        self.processor = SignalProcessor()
        self.intent_engine = IntentEngine()
        self.visualizer = Visualizer()
        self.cap = cv2.VideoCapture(0)
        self.frame_count = 0

    def run(self):
        if not self.cap.isOpened():
            print("Could not open webcam")
            return

        print("Starting pipeline... Press ESC to exit.")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            self.frame_count += 1
            t_ms = self.frame_count * int(1000 / self.config.FPS)

            # Detect
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.detector.detect(mp_image, t_ms)

            # Process
            current_clock_time = time.time()
            if result.pose_landmarks:
                lm = result.pose_landmarks[0]
                lm_xy = np.array([(l.x, l.y) for l in lm])
                self.processor.update(lm_xy, current_clock_time)
            else:
                self.processor.update_empty()

            # Compute Signals
            signals = self.processor.compute_signals(current_clock_time)
            
            # Intent Analysis
            intent_score, threat_level, norm_signals = self.intent_engine.update(signals)

            # Visualize
            self.visualizer.draw_overlay(frame, signals, intent_score, threat_level)
            self.visualizer.update_plots(self.processor.get_buffers()) # Could pass intent history too if we buffer it
            self.visualizer.show_frame(frame)

            if cv2.waitKey(1) & 0xFF == 27: # ESC
                break

        self.close()

    def close(self):
        self.cap.release()
        self.detector.close()
        self.visualizer.close()
