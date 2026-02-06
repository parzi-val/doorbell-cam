import multiprocessing
import queue
import cv2
import numpy as np
import onnxruntime as ort
from backend.config.config import Config

class WeaponDetector:
    def __init__(self, model_path=Config.WEAPON_MODEL_PATH):
        # Load ONNX model
        self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        
        model_inputs = self.session.get_inputs()
        self.input_name = model_inputs[0].name
        self.input_shape = model_inputs[0].shape
        self.output_name = self.session.get_outputs()[0].name
        
        self.conf_thres = Config.WEAPON_CONF_THRESH
        self.iou_thres = Config.WEAPON_IOU_THRESH
        self.classes = Config.WEAPON_CLASS_NAMES

    def preprocess(self, frame):
        # Resize to 640x640 (YOLOv8 default usually)
        self.img_height, self.img_width = frame.shape[:2]
        
        img = cv2.resize(frame, (Config.WEAPON_IMG_SIZE, Config.WEAPON_IMG_SIZE))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.transpose((2, 0, 1)) # HWC -> CHW
        img = np.expand_dims(img, axis=0)
        img = img.astype(np.float32) / 255.0
        return img

    def postprocess(self, output):
        # Output shape: [1, 4 + num_classes, 8400] -> [1, 84, 8400] for 80 classes
        # Transpose to [1, 8400, 84]
        predictions = np.transpose(output[0], (0, 2, 1))
        
        # predictions[0] is [8400, 84]
        # Box: [x, y, w, h]
        
        boxes = []
        scores = []
        class_ids = []
        
        # Iterate or vectorized? Vectorized is better.
        # Format: [cx, cy, w, h, class_score_1, class_score_2, ...]
        
        pred = predictions[0] # [8400, 4+nc]
        
        # Filter by confidence
        # Max class score
        class_scores = pred[:, 4:]
        max_scores = np.max(class_scores, axis=1)
        max_indices = np.argmax(class_scores, axis=1)
        
        mask = max_scores > self.conf_thres
        
        filtered_pred = pred[mask]
        filtered_scores = max_scores[mask]
        filtered_indices = max_indices[mask]
        
        if len(filtered_pred) == 0:
            return []
            
        # Boxes
        # cx, cy, w, h -> x1, y1, x2, y2
        cx = filtered_pred[:, 0]
        cy = filtered_pred[:, 1]
        w = filtered_pred[:, 2]
        h = filtered_pred[:, 3]
        
        x1 = cx - w/2
        y1 = cy - h/2
        x2 = cx + w/2
        y2 = cy + h/2
        
        # Scale back to original image size
        scale_x = self.img_width / Config.WEAPON_IMG_SIZE
        scale_y = self.img_height / Config.WEAPON_IMG_SIZE
        
        x1 *= scale_x
        y1 *= scale_y
        x2 *= scale_x
        y2 *= scale_y
        
        boxes_np = np.stack([x1, y1, x2-x1, y2-y1], axis=1) # xywh for NMS? 
        # OpenCV NMS expects [x, y, w, h]
        
        indices = cv2.dnn.NMSBoxes(
            bboxes=boxes_np.tolist(),
            scores=filtered_scores.tolist(),
            score_threshold=self.conf_thres,
            nms_threshold=self.iou_thres
        )
        
        results = []
        if len(indices) > 0:
            for i in indices.flatten():
                box = boxes_np[i]
                score = filtered_scores[i]
                class_id = filtered_indices[i]
                
                # Check bounds
                if class_id < len(self.classes):
                    class_name = self.classes[class_id]
                else:
                    class_name = f"Class {class_id}"
                
                results.append({
                    "box": box.astype(int).tolist(), # [x, y, w, h]
                    "score": float(score),
                    "class": class_name
                })
                
        return results

    def predict(self, frame):
        input_tensor = self.preprocess(frame)
        outputs = self.session.run([self.output_name], {self.input_name: input_tensor})
        detections = self.postprocess(outputs)
        return detections

class WeaponWorker(multiprocessing.Process):
    def __init__(self, model_path=Config.WEAPON_MODEL_PATH):
        super().__init__()
        self.daemon = True
        self.model_path = model_path
        self.queue = multiprocessing.Queue(maxsize=1) 
        self.result_queue = multiprocessing.Queue(maxsize=1)
        self.running = multiprocessing.Value('b', True)

    def process_frame(self, frame):
        if not self.running.value: return
        try:
            self.queue.put_nowait(frame)
        except queue.Full:
            pass 

    def get_latest_detections(self):
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self):
        self.running.value = False

    def run(self):
        # Init model inside process
        try:
            detector = WeaponDetector(self.model_path)
        except Exception as e:
            print(f"Failed to load Weapon model in worker: {e}")
            return
            
        while self.running.value:
            try:
                frame = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
                
            try:
                detections = detector.predict(frame)
                
                # Update result
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    pass
                self.result_queue.put(detections)
                
            except Exception as e:
                print(f"Weapon inference error: {e}")
