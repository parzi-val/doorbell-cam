# Doorbell Threat Detection

A behavioral analysis system for smart doorbells that detects suspicious intent using pose estimation signals.

## Features
- **Pose Estimation**: Powered by MediaPipe.
- **Signal Extraction**: Calculates signals like velocity, head yaw, hand fidgeting, and pacing (oscillation).
- **Intent Analysis**: Fuses detection signals to classify behavior as CALM, UNUSUAL, SUSPICIOUS, or THREAT.
- **Violence Detection**: Integrates MoViNet (Action Recognition) to treat violence probability as a "pressure" signal for intent modulation.
- **Hysteresis & Smoothing**: Uses EMA smoothing and threshold hysteresis for stable signal processing.

## Structure
- `backend/`: Core logic and pipeline implementation.
    - `core/`: Signal processing, intent engine, pose detection.
    - `config/`: Configuration for thresholds and weights.
    - `utils/`: Helper functions.
- `frontend/`: (Placeholder) Future web interface.
- `hardware/`: (Placeholder) Hardware integration.

## Usage
1. Install dependencies (see requirements, or ensure `mediapipe`, `opencv-python`, `numpy`, `matplotlib` are installed).
2. Run the pipeline:
   ```bash
   python backend/main.py
   ```
3. Press `ESC` to exit the live view.

## Configuration
Adjust sensitivity, thresholds, and weights in `backend/config/config.py`.
