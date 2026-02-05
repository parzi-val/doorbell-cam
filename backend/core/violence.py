import threading
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
        # Shape usually [1, 1, 2] (NoFight, Fight) or [1, 1, num_classes]
        # Or [1, 1] if binary? 
        # Notebook says: probs = tf.nn.softmax(logits)
        # And: CLASSES = ['Fight','No_Fight'] -> Wait.
        # Notebook cell 6: CLASSES = ['Fight','No_Fight']
        # But get_top_k uses this list.
        # We need to be careful about index order.
        # Usually alphabetical unless specified? 
        # MoViNet pretrained on Kinetics-600 has 600 classes.
        # The user says "binary: fight / no_fight".
        # If the user model is custom, let's look at the output shape.
        
        probs = tf.nn.softmax(logits)
        probs_np = probs.numpy()
        
        # Debug print to fix shape error
        # print(f"DEBUG: probs_np.shape = {probs_np.shape}")
        
        # Safe indexing based on observed error "array is 2-dimensional"
        # Most likely [1, 2] -> Batch 1, 2 Classes.
        # If [1, 2], probs_np[0] is [p0, p1]
        # We want Class 0 (assumed Fight for now based on notebook order in one cell, but inverted in another.. wait)
        # Notebook: CLASSES = ['Fight','No_Fight']
        # If model outputs [P(Fight), P(NoFight)], then index 0 is Fight.
        
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

class ViolenceWorker(threading.Thread):
    def __init__(self, model_path=Config.MOVINET_MODEL_PATH):
        super().__init__()
        self.daemon = True
        self.queue = queue.Queue(maxsize=1) # Drop old frames if busy
        try:
            self.detector = ViolenceDetector(model_path)
            self.running = True
        except Exception as e:
            print(f"Failed to load MoViNet model: {e}")
            self.detector = None
            self.running = False
            
        self.latest_prob = np.array([0.0, 0.0])
        self.lock = threading.Lock()

    def process_frame(self, frame):
        if not self.running: return
        
        # Non-blocking put. If full, drop frame (skip inference to catch up)
        try:
            self.queue.put_nowait(frame)
        except queue.Full:
            pass 

    def get_latest_probability(self):
        with self.lock:
            return self.latest_prob

    def run(self):
        if not self.detector: return
        
        while self.running:
            frame = self.queue.get()
            try:
                prob = self.detector.predict(frame)
                with self.lock:
                    self.latest_prob = prob
            except Exception as e:
                print(f"Violence inference error: {e}")
            finally:
                self.queue.task_done()
