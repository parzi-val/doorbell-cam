
from collections import deque
import numpy as np
from backend.config.config import Config
from backend.utils.geometry import dist
from backend.utils.smoothing import EMASmoother

class SignalProcessor:
    def __init__(self):
        self.centroid_buf = deque(maxlen=Config.WINDOW)
        self.vx_buf = deque(maxlen=Config.WINDOW)
        self.speed_buf = deque(maxlen=Config.WINDOW)
        self.raw_speed_buf = deque(maxlen=Config.WINDOW)
        self.head_yaw_buf = deque(maxlen=Config.WINDOW)
        self.head_down_buf = deque(maxlen=Config.WINDOW)
        self.hand_energy_buf = deque(maxlen=Config.WINDOW)
        
        self.first_centroid = None
        self.prev_wrists = None
        self.start_time = None # Set this when processing starts
        self.last_landmark_time = 0.0 # Track last successful detection
        
        # Loitering State
        self.loitering_start_pos = None
        self.loitering_clock = 0.0

        # Smoothers
        self.speed_smoother = EMASmoother(Config.EMA_ALPHA)
        self.vx_smoother = EMASmoother(Config.EMA_ALPHA)
        self.head_yaw_smoother = EMASmoother(Config.EMA_ALPHA)
        self.hand_energy_smoother = EMASmoother(Config.EMA_ALPHA)
        self.movinet_smoother = EMASmoother(Config.MOVINET_EMA_ALPHA)

        self.current_movinet_prob = 0.0
        self.prev_movinet_smoothed = 0.0
        
        # Debug Buffers for MoViNet
        self.movinet_p0_buf = deque(maxlen=Config.WINDOW)
        self.movinet_p1_buf = deque(maxlen=Config.WINDOW)
        
        # Weapon State
        self.weapon_debounce_buf = deque(maxlen=Config.WEAPON_DEBOUNCE_FRAMES)
        self.weapon_cooldown_expiry = 0.0
        
        # Doorbell State
        self.doorbell_rings = 0
        self.last_ring_time = 0.0
        self.doorbell_decay_rate = 0.5 # Rings lost per second

    def trigger_doorbell(self):
        """Called when hardware button is pressed."""
        import time
        now = time.time()
        # Debounce slightly at software level too (200ms)
        if now - self.last_ring_time > 0.2:
            self.doorbell_rings += 1.0
            self.last_ring_time = now
            print(f"[SIGNALS] Doorbell Ring! Count: {self.doorbell_rings}")

    def reset(self):
        """Reset all state and buffers."""
        self.centroid_buf.clear()
        self.vx_buf.clear()
        self.speed_buf.clear()
        self.raw_speed_buf.clear()
        self.head_yaw_buf.clear()
        self.head_down_buf.clear()
        self.hand_energy_buf.clear()
        self.movinet_p0_buf.clear()
        self.movinet_p1_buf.clear()
        self.weapon_debounce_buf.clear()
        
        self.first_centroid = None
        self.prev_wrists = None
        self.start_time = None
        self.last_landmark_time = 0.0
        
        self.loitering_start_pos = None
        self.loitering_clock = 0.0
        
        self.current_movinet_prob = 0.0
        self.prev_movinet_smoothed = 0.0
        self.weapon_cooldown_expiry = 0.0
        
        # Reset smoothers
        self.speed_smoother.reset()
        self.vx_smoother.reset()
        self.head_yaw_smoother.reset()
        self.hand_energy_smoother.reset()
        self.movinet_smoother.reset()

    def update(self, landmarks_xy, current_time, movinet_probs=None, weapon_detections=None):
        """
        Update buffers with new landmark data.
        :param landmarks_xy: np.array of shape (N, 2)
        :param current_time: float (timestamp)
        :param movinet_probs: np.array [p0, p1]
        :param weapon_detections: list of dicts
        """
        if movinet_probs is None: movinet_probs = np.array([0.0, 0.0])
        if weapon_detections is None: weapon_detections = []
        
        # Weapon Logic
        # Check if any detection > threshold (already filtered by worker, but good to be safe)
        has_weapon = len(weapon_detections) > 0
        self.weapon_debounce_buf.append(has_weapon)
        
        # Update MoViNet signal (using index 0 as 'fight' per previous logic, but buffering both)
        # Using simple raw buffering for graph
        self.movinet_p0_buf.append(movinet_probs[0])
        self.movinet_p1_buf.append(movinet_probs[1])
        
        # Keep pressure logic on index 0 for now (reverted logic)
        self.current_movinet_prob = self.movinet_smoother.update(movinet_probs[0])
        # Track last successful detection
        self.last_landmark_time = current_time

        # Indices
        NOSE = Config.NOSE
        LS, RS = Config.LS, Config.RS
        LH, RH = Config.LH, Config.RH
        LW, RW = Config.LW, Config.RW
        
        # Geometry
        hip_mid = landmarks_xy[[LH, RH]].mean(axis=0)
        shoulder_mid = landmarks_xy[[LS, RS]].mean(axis=0)
        nose = landmarks_xy[NOSE]
        
        if self.first_centroid is None:
            self.first_centroid = hip_mid.copy()

        self.centroid_buf.append(hip_mid)

        # Velocity
        if len(self.centroid_buf) > 1:
            dx = self.centroid_buf[-1][0] - self.centroid_buf[-2][0]
            vx = dx / Config.DT
            raw_speed = dist(self.centroid_buf[-1], self.centroid_buf[-2]) / Config.DT
        else:
            vx, raw_speed = 0.0, 0.0

        # Store raw speed for loitering logic (avoid smoothing lag)
        self.raw_speed_buf.append(raw_speed)

        # Apply smoothing
        speed = self.speed_smoother.update(raw_speed)
        vx = self.vx_smoother.update(vx)

        self.vx_buf.append(vx)
        self.speed_buf.append(speed)

        # Head yaw
        head_yaw = nose[0] - shoulder_mid[0]
        head_yaw = self.head_yaw_smoother.update(head_yaw)
        self.head_yaw_buf.append(head_yaw)

        # Head down
        self.head_down_buf.append(int(nose[1] > shoulder_mid[1]))

        # Hand motion
        wrists = [landmarks_xy[LW], landmarks_xy[RW]]
        if self.prev_wrists is not None:
            hand_energy = (
                dist(wrists[0], self.prev_wrists[0]) +
                dist(wrists[1], self.prev_wrists[1])
            )
        else:
            hand_energy = 0.0

        hand_energy = self.hand_energy_smoother.update(hand_energy)

        self.prev_wrists = wrists
        self.hand_energy_buf.append(hand_energy)

    def update_empty(self, movinet_probs=None, weapon_detections=None):
        """Update buffers when no pose is detected."""
        if movinet_probs is None: movinet_probs = np.array([0.0, 0.0])
        if weapon_detections is None: weapon_detections = []
        
        has_weapon = len(weapon_detections) > 0
        self.weapon_debounce_buf.append(has_weapon)
        self.movinet_p0_buf.append(movinet_probs[0])
        self.movinet_p1_buf.append(movinet_probs[1])
        
        self.current_movinet_prob = self.movinet_smoother.update(movinet_probs[0])
        self.vx_buf.append(0.0)
        self.speed_buf.append(0.0)
        self.raw_speed_buf.append(0.0)
        self.head_yaw_buf.append(0.0)
        self.head_down_buf.append(0)
        self.hand_energy_buf.append(0.0)

    def compute_signals(self, current_time):
        """
        Compute derived signals.
        :param current_time: float
        :return: dict
        """
        if self.start_time is None:
            self.start_time = current_time
            self.last_landmark_time = current_time

        # Check for timeout / Presence Reset
        if (current_time - self.last_landmark_time) > Config.PRESENCE_RESET_TIMEOUT:
            self.start_time = current_time # Reset presence start
        
        presence_duration = current_time - self.start_time
        
        # Ensure presence doesn't go negative if clocks skew slightly
        presence_duration = max(0.0, presence_duration)
        if not self.centroid_buf:
            return {}

        hip_mid = self.centroid_buf[-1]
        net_displacement = dist(self.first_centroid, hip_mid) if self.first_centroid is not None else 0.0

        # Motion Energy: Sum of speed * DT over the window
        # Reflects "how much have I moved recently" (path length)
        local_motion_energy = sum(self.speed_buf) * Config.DT
        
        centroid_velocity = np.mean(self.speed_buf) if self.speed_buf else 0.0
        
        # Loitering Score
        # "Standing at relatively the same place for a while"
        # Logic: If speed is low for > THRESH seconds -> loitering
        
        # Loitering Refactor
        # Initialize start pos on first valid detection in a sequence
        if self.loitering_start_pos is None:
            self.loitering_start_pos = hip_mid

        # Use RAW speed to catch fidgeting/micro-movements immediately
        current_raw_speed = self.raw_speed_buf[-1] if self.raw_speed_buf else 0.0
        
        # Displacement from the ORIGINAL loitering spot
        displacement = dist(self.loitering_start_pos, hip_mid)
        
        loitering_type = "NONE"
        loitering_radius = displacement
        
        # 3-Type Logic
        if current_raw_speed < Config.LOITERING_SPEED_THRESH:
            # Type 1: STATIONARY
            # Truly still. Standard time accumulation.
            self.loitering_clock += Config.DT
            loitering_type = "STATIONARY"
        
        elif displacement < Config.LOITERING_DISP_THRESH:
            # Type 2: PACING
            # Moving (speed > thresh) but staying in spot (disp < thresh).
            # Highly suspicious. Aggressive ramp.
            self.loitering_clock += Config.DT * 2.0 
            loitering_type = "PACING"
            
        else:
            # Type 3: DISPLACED
            # Moving AND left the spot. 
            # Reset logic.
            self.loitering_clock = 0.0
            self.loitering_start_pos = hip_mid # New spot
            loitering_type = "DISPLACED"
            
        # Calculate Score
        # Ramp from 0 to 1 after TIME_THRESH
        if self.loitering_clock > Config.LOITERING_TIME_THRESH:
            over_time = self.loitering_clock - Config.LOITERING_TIME_THRESH
            loitering_score = min(over_time / 5.0, 1.0)
        else:
            loitering_score = 0.0

        head_yaw_rate = np.mean(np.abs(np.diff(self.head_yaw_buf))) if len(self.head_yaw_buf) > 1 else 0.0

        # Head Oscillation with Hysteresis
        # Count 0-crossings with hysteresis state
        head_oscillation = 0
        osc_state = 0 # 0: neutral, 1: positive (> hyst), -1: negative (< -hyst)
        for val in self.head_yaw_buf:
            if osc_state == 0:
                if val > Config.HEAD_YAW_HYST: osc_state = 1
                elif val < -Config.HEAD_YAW_HYST: osc_state = -1
            elif osc_state == 1:
                if val < -Config.HEAD_YAW_HYST:
                    osc_state = -1
                    head_oscillation += 1
            elif osc_state == -1:
                if val > Config.HEAD_YAW_HYST:
                    osc_state = 1
                    head_oscillation += 1

        head_down_fraction = sum(self.head_down_buf) / len(self.head_down_buf) if self.head_down_buf else 0.0

        # Centroid-based Direction Reversal & Oscillation Energy
        direction_reversal = 0
        oscillation_energy = 0.0
        
        if len(self.centroid_buf) > 1:
            # Calculate dx array
            # We need to iterate buffers. They are deques.
            # Let's convert to list for slicing.
            c_x = [p[0] for p in self.centroid_buf]
            dxs = np.diff(c_x)
            
            # Direction Flip
            dir_state = 0 # 0: neutral, 1: right, -1: left
            for dx in dxs:
                if abs(dx) > Config.CENTROID_DX_THRESH:
                    current_dir = 1 if dx > 0 else -1
                    if dir_state != 0 and current_dir != dir_state:
                         direction_reversal += 1
                    dir_state = current_dir
            
            # Oscillation Energy
            # osc_energy = np.mean(np.abs(np.diff(np.sign(dx_buf))))
            # We use the same dxs
            if len(dxs) > 1:
                oscillation_energy = np.mean(np.abs(np.diff(np.sign(dxs))))

        # Robust Stop/Go
        # Count transitions into stopped state? or into moving state?
        # User said "Stop/Go", usually implies "start-stop-start-stop" behavior.
        stop_go = 0
        is_stopped = True # Assume stopped initially or track state?
        # Let's iterate.
        if self.speed_buf:
            # Determine initial state based on first sample
            is_stopped = self.speed_buf[0] < Config.STOP_THRESHOLD
            
            for i in range(1, len(self.speed_buf)):
                val = self.speed_buf[i]
                if is_stopped:
                    if val > Config.STOP_THRESHOLD * 1.5: # Hysteresis for starting
                        is_stopped = False
                        stop_go += 1 # Count a "Go" (start)
                else:
                    if val < Config.STOP_THRESHOLD:
                        is_stopped = True
                        # stop_go += 1 # Or count Stops? Let's count starts.
        else:
            stop_go = 0

        # High-pass hand fidget
        hand_fidget = (
            np.mean(np.abs(np.diff(self.hand_energy_buf)))
            if len(self.hand_energy_buf) > 1 else 0.0
        )
        
        # MoViNet Pressure
        # Base pressure (deviation from baseline)
        delta = self.current_movinet_prob - Config.MOVINET_PRESSURE_THRESH
        base_pressure = max(0.0, delta) * Config.MOVINET_PRESSURE_GAIN
        
        # Slope pressure (positive rate of change)
        dp = self.current_movinet_prob - self.prev_movinet_smoothed
        slope_pressure = max(0.0, dp) * Config.MOVINET_SLOPE_GAIN
        
        self.prev_movinet_smoothed = self.current_movinet_prob
        
        movinet_pressure = base_pressure + slope_pressure
        
        # Weapon Confirmation (Debounced & Cooldown)
        # Only confirm if ALL frames in the buffer are True
        raw_weapon_confirmed = False
        if len(self.weapon_debounce_buf) == self.weapon_debounce_buf.maxlen:
            raw_weapon_confirmed = all(self.weapon_debounce_buf)
            
        # Update Cooldown
        if raw_weapon_confirmed:
            self.weapon_cooldown_expiry = current_time + Config.WEAPON_COOLDOWN_S
            
        # Check active status
        weapon_confirmed = False
        if current_time < self.weapon_cooldown_expiry:
             weapon_confirmed = True
             
        # Doorbell Decay (assuming Config.DT is the dt for decay)
        if Config.DT > 0:
            self.doorbell_rings = max(0.0, self.doorbell_rings - (self.doorbell_decay_rate * Config.DT))
        
        weapon_cooldown = max(0.0, self.weapon_cooldown_expiry - current_time)
        
        return {
            "presence_s": presence_duration,
            "doorbell_rings": self.doorbell_rings,
            "net_disp": net_displacement,
            "motion_E": local_motion_energy,
            "velocity": centroid_velocity,
            "head_yaw_rate": head_yaw_rate,
            "head_osc": head_oscillation,
            "head_down": head_down_fraction,
            "dir_flip": direction_reversal,
            "osc_energy": oscillation_energy,
            "stop_go": stop_go,
            "hand_fidget": hand_fidget,
            "movinet_pressure": movinet_pressure,
            "loitering_score": loitering_score,
            "loitering_type": loitering_type,
            "loitering_time": self.loitering_clock,
            "loitering_radius": loitering_radius,
            "weapon_confirmed": weapon_confirmed,
            "weapon_cooldown": weapon_cooldown
        }

    def get_buffers(self):
        return {
            "velocity": list(self.speed_buf),
            "head_yaw": list(self.head_yaw_buf),
            "hand_fidget": list(self.hand_energy_buf),
            "movinet_p0": list(self.movinet_p0_buf),
            "movinet_p1": list(self.movinet_p1_buf),
            "motion_E_len": len(self.centroid_buf) # Just returning length for x-axis gen
        }
