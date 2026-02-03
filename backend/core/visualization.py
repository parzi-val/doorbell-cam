
import cv2
import matplotlib.pyplot as plt
from backend.config.config import Config

class Visualizer:
    def __init__(self):
        self.config = Config
        
        # Matplotlib setup
        plt.ion()
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

    def draw_overlay(self, frame, signals, intent_score=0.0, threat_level="CALM"):
        """
        Draw text overlay on the frame.
        :param frame: cv2 image
        :param signals: dict of signal values
        :param intent_score: float
        :param threat_level: str
        """
        y = 20
        # Intent Overlay
        cv2.putText(frame, f"INTENT: {intent_score:.2f} | {threat_level}", (10, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if intent_score > 0.5 else (0, 255, 0), 2)
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
