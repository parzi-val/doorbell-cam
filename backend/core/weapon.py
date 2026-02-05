import threading
import queue
import time
import numpy as np
import cv2
import onnxruntime as ort
from backend.config.config import Config

class WeaponDetector:
    def __init__(self, model_path=Config.WEAPON_MODEL_PATH):
        try:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self.session = ort.InferenceSession(model_path, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            self.img_size = Config.WEAPON_IMG_SIZE
        except Exception as e:
            print(f"Failed to initialize WeaponDetector: {e}")
            self.session = None

    def preprocess(self, img):
        img_resized = cv2.resize(img, (self.img_size, self.img_size))
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_normalized = img_rgb.astype(np.float32) / 255.0
        img_transposed = img_normalized.transpose(2, 0, 1)
        img_batch = np.expand_dims(img_transposed, axis=0)
        return img_batch

    def xywh2xyxy(self, x):
        y = np.copy(x)
        y[0] = x[0] - x[2] / 2  # x1
        y[1] = x[1] - x[3] / 2  # y1
        y[2] = x[0] + x[2] / 2  # x2
        y[3] = x[1] + x[3] / 2  # y2
        return y

    def nms(self, boxes, scores):
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]

        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h

            iou = inter / (areas[i] + areas[order[1:]] - inter)
            inds = np.where(iou <= Config.WEAPON_IOU_THRESH)[0]
            order = order[inds + 1]

        return keep

    def predict(self, frame):
        if self.session is None: return []

        original_shape = frame.shape[:2]
        img_input = self.preprocess(frame)

        outputs = self.session.run([self.output_name], {self.input_name: img_input})
        
        # Postprocess
        output = outputs[0]
        predictions = output[0].transpose()
        
        boxes = predictions[:, :4]
        scores = predictions[:, 4:]
        
        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)
        
        mask = confidences > Config.WEAPON_CONF_THRESH
        boxes = boxes[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]
        
        if len(boxes) == 0:
            return []
            
        boxes_xyxy = np.array([self.xywh2xyxy(box) for box in boxes])
        
        # Scale boxes
        scale_x = original_shape[1] / self.img_size
        scale_y = original_shape[0] / self.img_size
        boxes_xyxy[:, [0, 2]] *= scale_x
        boxes_xyxy[:, [1, 3]] *= scale_y
        
        indices = self.nms(boxes_xyxy, confidences)
        
        detections = []
        for i in indices:
            detections.append({
                'box': boxes_xyxy[i].astype(int),
                'confidence': float(confidences[i]),
                'class_id': int(class_ids[i]),
                'class_name': Config.WEAPON_CLASS_NAMES[class_ids[i]] if class_ids[i] < len(Config.WEAPON_CLASS_NAMES) else f"Class {class_ids[i]}"
            })
            
        return detections

class WeaponWorker(threading.Thread):
    def __init__(self, model_path=Config.WEAPON_MODEL_PATH):
        super().__init__()
        self.daemon = True
        self.queue = queue.Queue(maxsize=1)
        self.detector = WeaponDetector(model_path)
        self.running = True if self.detector.session else False
        self.latest_detections = []
        self.lock = threading.Lock()

    def process_frame(self, frame):
        if not self.running: return
        try:
            self.queue.put_nowait(frame)
        except queue.Full:
            pass

    def get_latest_detections(self):
        with self.lock:
            return self.latest_detections

    def run(self):
        if not self.running: return
        
        while self.running:
            frame = self.queue.get()
            try:
                detections = self.detector.predict(frame)
                with self.lock:
                    self.latest_detections = detections
            except Exception as e:
                print(f"Weapon inference error: {e}")
            finally:
                self.queue.task_done()
