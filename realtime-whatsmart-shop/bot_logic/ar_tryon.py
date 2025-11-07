# Simplified, safe MediaPipe + OpenCV overlay example
import cv2, mediapipe as mp, numpy as np, requests

mp_pose = mp.solutions.pose.Pose(static_image_mode=True)

def overlay_shoes(user_img_url: str, product_png_url: str):
    user_bytes   = requests.get(user_img_url).content
    product_bytes = requests.get(product_png_url).content
    img  = cv2.imdecode(np.frombuffer(user_bytes, np.uint8), cv2.IMREAD_COLOR)
    shoe = cv2.imdecode(np.frombuffer(product_bytes, np.uint8), cv2.IMREAD_UNCHANGED)

    results = mp_pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if not results.pose_landmarks:
        raise ValueError("No person detected")

    # Use ankle landmarks for placement
    h, w = img.shape[:2]
    left_ankle  = results.pose_landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_ANKLE]
    right_ankle = results.pose_landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_ANKLE]

    for ankle in [left_ankle, right_ankle]:
        x, y = int(ankle.x * w), int(ankle.y * h)
        shoe_resized = cv2.resize(shoe, (100, 50))
        alpha = shoe_resized[:, :, 3] / 255.0
        for c in range(3):
            y1, y2 = y-50, y
            x1, x2 = x-50, x+50
            if 0 <= y1 < h and 0 <= x1 < w:
                img[y1:y2, x1:x2, c] = (
                    alpha * shoe_resized[:, :, c] +
                    (1 - alpha) * img[y1:y2, x1:x2, c]
                )
    ok, buf = cv2.imencode(".png", img)
    return buf.tobytes()
