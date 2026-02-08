
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from backend.config.config import Config

class PoseDetector:
    def __init__(self):
        self._init_detector()

    def _init_detector(self):
        base_options = python.BaseOptions(model_asset_path=Config.MODEL_PATH)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)

    def reset(self):
        if hasattr(self, 'landmarker'):
            self.landmarker.close()
        self._init_detector()

    def detect(self, image, timestamp_ms):
        """
        Detect poses in the given RGB image.
        :param image: mp.Image object
        :param timestamp_ms: int
        :return: vision.PoseLandmarkerResult
        """
        return self.landmarker.detect_for_video(image, timestamp_ms)

    def close(self):
        self.landmarker.close()
