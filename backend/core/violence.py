import multiprocessing
import queue
import time
import numpy as np
import tensorflow as tf
import cv2
from ai_edge_litert.interpreter import Interpreter
from backend.config.config import Config

class ViolenceDetector:
    def __init__(self, model_path=Config.MOVINET_MODEL_PATH):
        self.interpreter = Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        
        # Use SignatureRunner for robust input/output mapping
        self.runner = self.interpreter.get_signature_runner()
        
        # State initialization
        self.input_details = self.runner.get_input_details()
        self.output_details = self.runner.get_output_details()
        
        # Initialize states
        # The notebook pops "image" from input details to get pure states
        self.states = {}
        for name, info in self.input_details.items():
            if name != 'image':
                self.states[name] = np.zeros(info['shape'], dtype=info['dtype'])

        # Store input shape for resizing
        # We assume 'image' key exists and is the visual input
        if 'image' in self.input_details:
            self.input_shape = self.input_details['image']['shape'] # e.g. [1, 1, 172, 172, 3]
        else:
            # Fallback or error
            print("Warning: 'image' input not found in signature. Using Default.")
            # Trying to find the 5D input
            for name, info in self.input_details.items():
                if len(info['shape']) == 5:
                    self.input_shape = info['shape']
                    break

    def predict(self, frame):
        """
        Process a single frame and return the probability of 'Fight'.
        Args:
            frame: BGR image (numpy array)
        Returns:
            float: Probability of fight [0.0, 1.0]
        """
        # Preprocess
        # Resize to input shape (usually 172x172)
        # input_shape is [1, 1, H, W, 3]
        if len(self.input_shape) == 5:
            target_h, target_w = self.input_shape[2], self.input_shape[3]
        else:
            target_h, target_w = 172, 172 # Default fallback

        img = cv2.resize(frame, (target_w, target_h))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.expand_dims(img, axis=0) # [1, H, W, 3]
        img = np.expand_dims(img, axis=0) # [1, 1, H, W, 3]

        # Run inference using signature runner
        # Pass image and current states
        # **self.states unpacks the state dict
        outputs = self.runner(image=img, **self.states)
        
        # Extract logits and update states
        # outputs contains new states and 'logits'
        logits = outputs.pop('logits')
        self.states = outputs # The rest are the new states
        
        # Process logits
        probs = tf.nn.softmax(logits)
        probs_np = probs.numpy()
        
        if len(probs_np.shape) == 2:
             # Log raw probabilities for verification
             if np.max(probs_np[0]) > 0.1: 
                 # print(f"MoViNet Raw: {probs_np[0]}")
                 pass
             
             return probs_np[0] # Return [p0, p1]
             
        elif len(probs_np.shape) == 3:
             return probs_np[0, 0] # Return [p0, p1]
        else:
             return np.array([0.0, 0.0])

class ViolenceWorker(multiprocessing.Process):
    def __init__(self, model_path=Config.MOVINET_MODEL_PATH):
        super().__init__()
        self.daemon = True
        self.model_path = model_path
        self.queue = multiprocessing.Queue(maxsize=1) 
        self.result_queue = multiprocessing.Queue(maxsize=1)
        self.running = multiprocessing.Value('b', True) # Boolean flag

    def process_frame(self, frame):
        if not self.running.value: return
        try:
            self.queue.put_nowait(frame)
        except queue.Full:
            pass 

    def get_latest_probability(self):
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None # Return None to indicate no new update, or handle differently in pipeline

    def stop(self):
        self.running.value = False

    def run(self):
        # Initialize model INSIDE the process to avoid pickling issues
        try:
            detector = ViolenceDetector(self.model_path)
            last_prob = np.array([0.0, 0.0])
        except Exception as e:
            print(f"Failed to load MoViNet model in worker: {e}")
            return
        
        while self.running.value:
            try:
                frame = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
                
            try:
                prob = detector.predict(frame)
                
                # Update result
                # We want to clear the old result if possible to keep it fresh
                try:
                    self.result_queue.get_nowait() # consume old
                except queue.Empty:
                    pass
                self.result_queue.put(prob)
                
            except Exception as e:
                print(f"Violence inference error: {e}")
