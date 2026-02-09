
import os
import json
import numpy as np
import time
from datetime import datetime
from backend.config.config import IntentConfig

class LearningSystem:
    def __init__(self):
        # Mirror IntentConfig
        self.weights = IntentConfig.WEIGHTS.copy()
        self.norm_max = IntentConfig.NORM_MAX.copy()
        
        # Hyperparameters for "Simulation"
        self.learning_rate = 0.05
        
        # Directories
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.logs_dir = os.path.join(self.base_dir, "logs")
        self.learning_dir = os.path.join(self.logs_dir, "learning")
        self.meta_dir = os.path.join(self.logs_dir, "metadata")
        
        os.makedirs(self.learning_dir, exist_ok=True)

    def sigmoid(self, x):
        return 1 / (1 + np.exp(-x))

    def normalize(self, signals):
        norm_signals = {}
        for key, max_val in self.norm_max.items():
            val = signals.get(key, 0.0)
            if isinstance(val, dict): val = val.get("max", 0.0) # Handle stats dict
            norm_val = min(val / max_val, 1.0)
            norm_signals[key] = max(0.0, norm_val)
        return norm_signals

    def calculate_prediction(self, norm_signals):
        # Simplified linear model matching IntentEngine (roughly)
        # Score = Sum(w * s) + Bias (simulated)
        score = 0.0
        contributions = {}
        
        for key, weight in self.weights.items():
            val = norm_signals.get(key, 0.0)
            contrib = val * weight
            score += contrib
            contributions[key] = contrib
            
        return score, contributions

    def process_feedback(self, event_id, feedback_type):
        """
        feedback_type: "accurate" (Positive) or "inaccurate" (Negative)
        """
        # 1. Load Event Data
        meta_path = os.path.join(self.meta_dir, f"{event_id}.json")
        # Fallback search if filename doesn't match ID exactly (id is inside json)
        if not os.path.exists(meta_path):
             # Try searching content? No, strictly assume filename matches for now or passed path
             # Actually, server passes full event object or we glob. 
             # Let's glob for ID if not direct match.
             import glob
             files = glob.glob(os.path.join(self.meta_dir, "*.json"))
             for f in files:
                 with open(f, 'r') as jf:
                     try:
                        d = json.load(jf)
                        if d.get("clip_id") == event_id:
                            meta_path = f
                            break
                     except: pass
        
        if not os.path.exists(meta_path):
            return {"error": "Event not found"}
            
        with open(meta_path, 'r') as f:
            event_data = f.read()
            event = json.loads(event_data)

        # 2. Determine Target
        # If "Accurate":
        #   - If THREAT/SUSPICIOUS -> Target = 1.0
        #   - If CALM -> Target = 0.0
        # If "Inaccurate":
        #   - If THREAT/SUSPICIOUS -> Target = 0.0 (False Positive)
        #   - If CALM -> Target = 1.0 (False Negative)
        
        level = event.get("final_level", "CALM")
        is_threat = level in ["THREAT", "SUSPICIOUS", "UNUSUAL"] # Grouping active states
        
        if feedback_type == "accurate":
            target = 1.0 if is_threat else 0.0
        else:
            target = 0.0 if is_threat else 1.0
            
        # 3. Simulate Forward Pass
        # Use "signals_stats" -> "max" as the representative value for the event
        signals_raw = {}
        stats = event.get("signals_stats", {})
        for k, v in stats.items():
            if isinstance(v, dict):
                signals_raw[k] = v.get("max", 0.0)
            else:
                signals_raw[k] = v
                
        norm_signals = self.normalize(signals_raw)
        prediction_score, contributions = self.calculate_prediction(norm_signals)
        
        # Sigmoid for probability-like error calc (Optional, but helps with gradients)
        pred_prob = self.sigmoid(prediction_score * 5 - 2.5) # Scaling to make linear score 0.5 center around 0
        # Actually, let's stick to linear error for interpretable weight deltas on the linear weights
        
        error = target - prediction_score
        
        # 4. Calculate Gradients / Deltas
        # Delta W = LearningRate * Error * Input
        weight_deltas = {}
        for key, input_val in norm_signals.items():
            if key in self.weights:
                delta = self.learning_rate * error * input_val
                weight_deltas[key] = delta
                
        # 5. Credit Assignment
        # Which specific interaction contributed most to the error?
        # If False Positive (Target 0, Pred High): High inputs with high weights are to blame.
        # If False Negative (Target 1, Pred Low): Low weights or Low inputs are to blame.
        
        blame_report = []
        sorted_contribs = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        
        if target == 0.0 and prediction_score > 0.3: # False Positive Analysis
            for k, v in sorted_contribs:
                if v > 0.05:
                    blame_report.append(f"{k} contributed {v:.2f} (Val: {norm_signals[k]:.2f} * W: {self.weights[k]})")
                    
        elif target == 1.0 and prediction_score < 0.6: # False Negative Analysis
            # Find high interaction potential (high input, low weight) or missed signals
            for k, w in self.weights.items():
                val = norm_signals.get(k, 0.0)
                if val > 0.5:
                    blame_report.append(f"{k} was high ({val:.2f}) but weight ({w}) might be too low.")
        
        # 6. Conclusion Generation
        conclusion = "No significant adjustment needed."
        if abs(error) > 0.1:
            if target == 1.0:
                conclusion = "Model under-confident. Consider increasing weights for observed active signals."
            else:
                # Find biggest weight delta (negative)
                min_delta_k = min(weight_deltas, key=weight_deltas.get)
                conclusion = f"Model over-confident. {min_delta_k} caused false alarm; generated weight penalty of {weight_deltas[min_delta_k]:.4f}."

        # 7. Save Report
        # Use high-res timestamp and feedback type to avoid collisions
        ts = int(time.time() * 1000)
        report_id = f"report_{event_id}_{feedback_type}_{ts}"
        report = {
            "report_id": report_id,
            "event_id": event_id,
            "timestamp": time.time(),
            "feedback": feedback_type,
            "model_state": {
                "prediction": prediction_score,
                "target": target,
                "error": error
            },
            "weight_updates": weight_deltas,
            "credit_assignment": blame_report,
            "conclusion": conclusion
        }
        
        with open(os.path.join(self.learning_dir, f"{report_id}.json"), 'w') as f:
            json.dump(report, f, indent=4)
            
        return report
