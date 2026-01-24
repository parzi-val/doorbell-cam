import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


MODEL_PATH = "models/pose/pose_landmarker_lite.task"


# MediaPipe Pose connections (hardcoded, stable)
POSE_CONNECTIONS = [
    (11, 13), (13, 15),   # left arm
    (12, 14), (14, 16),   # right arm
    (11, 12),             # shoulders
    (23, 24),             # hips
    (11, 23), (12, 24),   # torso
    (23, 25), (25, 27),   # left leg
    (24, 26), (26, 28),   # right leg
]


def draw_pose(frame, landmarks):
    h, w, _ = frame.shape

    # Draw joints
    for lm in landmarks:
        cx, cy = int(lm.x * w), int(lm.y * h)
        cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

    # Draw bones
    for a, b in POSE_CONNECTIONS:
        x1, y1 = int(landmarks[a].x * w), int(landmarks[a].y * h)
        x2, y2 = int(landmarks[b].x * w), int(landmarks[b].y * h)
        cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

    return frame


def main():
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)

    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1
    )

    landmarker = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam")

    timestamp_ms = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = landmarker.detect_for_video(mp_image, timestamp_ms)
        timestamp_ms += 33  # ~30 FPS

        if result.pose_landmarks:
            frame = draw_pose(frame, result.pose_landmarks[0])

        cv2.imshow("Pose (raw landmarks)", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()


if __name__ == "__main__":
    main()
