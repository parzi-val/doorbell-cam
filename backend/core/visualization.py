
import cv2
import matplotlib.pyplot as plt
from backend.config.config import Config

class Visualizer:
    def __init__(self):
        self.config = Config
        
        # Matplotlib setup
        plt.ion()
        # DEBUG: Only plotting MoViNet classes as requested
        self.fig, self.ax = plt.subplots(1, 1, figsize=(7, 4))
        self.lines = {
            "movinet_p0": self.ax.plot([], [], label="Class 0 (Fight?)", color='r')[0],
            "movinet_p1": self.ax.plot([], [], label="Class 1 (NoFight?)", color='b')[0],
        }
        
        self.ax.legend()
        self.ax.set_xlim(0, self.config.WINDOW)
        self.ax.set_ylim(0, 1.0)

    def draw_overlay(self, frame, signals, intent_score=0.0, threat_level="CALM", weapon_detections=None, is_recording=False):
        """
        Draw signal values and intent score on the frame.
        """
        if weapon_detections is None: weapon_detections = []
        
        h, w, _ = frame.shape
        
        # Draw Weapon Detections first (under overlay)
        # ... (Already detected) ...
        # But wait, replace call replaces range. I need to keep the drawing loop? 
        # The drawing loop is lines 34-43 in original file which is inside current view.
        # I should output the WHOLE function or be careful.
        # I will replace from __init__ down to keys list.
        
        for det in weapon_detections:
            box = det['box']
            conf = det['score']
            name = det['class']
            
            # Color: Red for high confidence
            color = (0, 0, 255) 
            cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)
            label = f"{name} {conf:.2f}"
            cv2.putText(frame, label, (box[0], box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Background panel for text
        panel_w = 280
        
        y = 20
        # Intent Overlay
        # Logic: Red if weapon confirmed or high score
        if is_recording:
            cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1) # Red dot
            cv2.putText(frame, "REC", (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        
        color = (0, 255, 0)
        is_weapon = signals.get('weapon_confirmed', False)
        
        if is_weapon:
            score_str = f"INTENT: {intent_score:.2f} | WEAPON DETECTED"
            color = (0, 0, 255)
        else:
            score_str = f"INTENT: {intent_score:.2f} | {threat_level}"
            if intent_score > 0.5: color = (0, 0, 255)
            elif intent_score > 0.3: color = (0, 165, 255) # Orange-ish

        cv2.putText(frame, score_str, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        y += 30

        # signal keys to display in order
        keys = [
            ("presence_s", signals.get("presence_s", 0)),
            ("net_disp", signals.get("net_disp", 0)),
            ("motion_E", signals.get("motion_E", 0)),
            ("velocity", signals.get("velocity", 0)),
            ("head_yaw_rate", signals.get("head_yaw_rate", 0)),
            ("head_osc", signals.get("head_osc", 0)),
            ("head_down", signals.get("head_down", 0)),
            ("dir_flip", signals.get("dir_flip", 0)),
            ("osc_energy", signals.get("osc_energy", 0)),
            ("stop_go", signals.get("stop_go", 0)),
            ("hand_fidget", signals.get("hand_fidget", 0)),
            ("movinet_p", signals.get("movinet_pressure", 0)),
            ("weapon_confirmed", 1.0 if is_weapon else 0.0),
            ("weapon_timer", signals.get("weapon_cooldown", 0)),
        ]
        
        for name, val in keys:
            cv2.putText(
                frame,
                f"{name}: {val:.3f}",
                (10, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 0),
                1
            )
            y += 15

    def update_plots(self, buffers):
        """
        Update live plots.
        :param buffers: dict containing lists for plots
        """
        plot_data = {
            "movinet_p0": buffers.get("movinet_p0", []),
            "movinet_p1": buffers.get("movinet_p1", []),
        }

        for key, line in self.lines.items():
            ydata = plot_data.get(key, [])
            xdata = list(range(len(ydata)))
            line.set_data(xdata, ydata)
            
            # Fixed Y-limit 0-1 for probabilities
        
        plt.pause(0.001)

    def show_frame(self, frame):
        cv2.imshow("Pose Signals (Live)", frame)

    def close(self):
        cv2.destroyAllWindows()
        plt.close(self.fig)
