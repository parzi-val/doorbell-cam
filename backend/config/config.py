import os

class Config:
    # Model settings
    MODEL_PATH = "models/pose/pose_landmarker_lite.task"
    MOVINET_MODEL_PATH = "models/violence/model.tflite"
    
    # Camera / Pipeline settings
    FPS = 30
    DT = 1.0 / FPS
    WINDOW = 30  # Buffered frames (approx 1 second)
    EMA_ALPHA = 0.6 # Smoothing factor (0 < alpha <= 1)
    
    # Signal Thresholds / Hysteresis
    HEAD_YAW_HYST = 0.02  # Lowered from 0.05
    VELOCITY_HYST = 0.1   # ~0.003 movement per frame
    CENTROID_DX_THRESH = 0.005 # Normalized units for direction flip
    STOP_THRESHOLD = 0.2  # Speed below this is "stopped"
    
    # Loitering
    LOITERING_TIME_THRESH = 4.0 # Seconds before loitering signal starts ramping
    LOITERING_DISP_THRESH = 0.3 # Max net displacement to consider "in place"
    LOITERING_SPEED_THRESH = 0.03 # Speed below which is considered "stationary" for loitering
    
    # Landmark indices
    NOSE = 0
    LS, RS = 11, 12
    LH, RH = 23, 24
    LW, RW = 15, 16
    LA, RA = 27, 28

    # Presence Logic
    PRESENCE_RESET_TIMEOUT = 2.0 # seconds without detection to reset presence

    # MoViNet settings
    MOVINET_EMA_ALPHA = 0.1
    MOVINET_PRESSURE_THRESH = 0.1 # Lowered for testing visibility
    MOVINET_PRESSURE_GAIN = 2.0
    MOVINET_SLOPE_GAIN = 1.0

    # Weapon Detection Settings
    WEAPON_MODEL_PATH = "models/weapons/best.onnx"
    WEAPON_IMG_SIZE = 640
    WEAPON_CONF_THRESH = 0.6
    WEAPON_IOU_THRESH = 0.45
    WEAPON_DEBOUNCE_FRAMES = 3
    WEAPON_COOLDOWN_S = 20.0
    WEAPON_CLASS_NAMES = ['Gun', 'Explosive', 'Grenade', 'Knife']

    # Clip & Logging Settings
    # Clip & Logging Settings
    LOG_DIR = "logs"
    CLIP_DURATION_SECONDS = 60
    CLIP_COOLDOWN_SECONDS = 60
    
    
    # GenAI
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Dev
    NO_LOGS = os.getenv("NO_LOGS", "false").lower() == "true"

class IntentConfig:
    # Normalization Max Values (Approximate upper bounds)
    NORM_MAX = {
        "velocity": 2.0,       # m/s or relative units
        "motion_E": 2.0,       # Increased range to handle fast movers
        "head_yaw_rate": 0.5,  # rad/s ? Adjust based on observation
        "head_osc": 5,         # count per window
        "hand_fidget": 0.2,    # high pass energy
        "osc_energy": 1.0,     # mean abs diff sign dx (0-2 range usually)
        "head_down": 1.0,      # fraction
        "dir_flip": 5,         # count per window
        "stop_go": 5,          # count per window
        "presence_s": 60,      # seconds (maybe less relevant for immediate intent?)
        "movinet_pressure": 1.0, # Normalized pressure derived from probability
        "loitering_score": 1.0 # 0-1 score
    }
    
    INTENT_HARDBOOST_VALUE = 0.8

    # Fusion Weights (Sum doesn't strictly need to be 1, but intent score should be 0-1 range usually)
    # We will clip the final score.
    WEIGHTS = {
        "velocity": 0.1,
        "motion_E": 0.1,
        "head_yaw_rate": 0.1,
        "head_osc": 0.1,
        "hand_fidget": 0.1,
        "osc_energy": 0.1,
        "head_down": 0.1,
        "dir_flip": 0.1,
        "stop_go": 0.05,
        "movinet_pressure": 0.2, # Increased from 0.15
        "loitering_score": 0.25 # High importance for loitering
    }

    # Intent Smoothing
    INTENT_ALPHA = 0.1 # Slower smoothing for stability

    # Threat Thresholds
    TH_CALM = 0.4
    TH_UNUSUAL = 0.6
    TH_SUSPICIOUS = 0.7
    # THREAT >= 0.65

    # Presence Logic
    PRESENCE_RAMP_MIN = 20  # seconds
    PRESENCE_RAMP_MAX = 60  # seconds
    PRESENCE_GATING_FACTOR = 2.0

