import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import joblib
import numpy as np
from collections import deque
import paho.mqtt.client as mqtt
import os
import contextlib

from gesture_config import LABEL_TO_COMMAND

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17), (5, 17),
]


def draw_hand_landmarks(image, hand_landmarks):
    h, w, _ = image.shape
    for start_idx, end_idx in HAND_CONNECTIONS:
        start = hand_landmarks[start_idx]
        end = hand_landmarks[end_idx]
        cv2.line(
            image,
            (int(start.x * w), int(start.y * h)),
            (int(end.x * w), int(end.y * h)),
            (0, 255, 0),
            2,
        )
    for lm in hand_landmarks:
        cv2.circle(image, (int(lm.x * w), int(lm.y * h)), 4, (0, 0, 255), -1)

# --- CẤU HÌNH MQTT ---
BROKER = "broker.emqx.io" # Trạm trung chuyển miễn phí
PORT = 1883
TOPIC = "artemis/robot/command" # Tên kênh của nhóm mình (phải độc nhất)

# Khởi tạo kết nối
print("Đang kết nối tới trạm MQTT...")
mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()
print("Đã kết nối MQTT thành công!")

# Biến để chống spam mạng (Chỉ gửi khi có lệnh MỚI)
last_sent_command = None

# 1. Tải mô hình
MODEL_FILE = os.path.join(os.path.dirname(__file__), "gesture_model.pkl")
if not os.path.isfile(MODEL_FILE):
    raise FileNotFoundError(
        "Chưa có file 'gesture_model.pkl'. Hãy chạy hand_tracking.py để thu dữ liệu, rồi chạy train_model.py để tạo model."
    )
model = joblib.load(MODEL_FILE)

COMMAND_MAP = LABEL_TO_COMMAND

# Giảm/tăng ngưỡng này để nhận diện nhạy hơn hoặc chắc chắn hơn
MIN_CONFIDENCE = 0.65

# --- BỘ LỌC CHỐNG DỘI TÍN HIỆU (DEBOUNCE) ---
# Lưu tối đa 5 kết quả gần nhất
command_history = deque(maxlen=5) 

HAND_LANDMARKER_MODEL = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
if not os.path.isfile(HAND_LANDMARKER_MODEL):
    raise FileNotFoundError(
        "Thiếu file 'hand_landmarker.task'. Hãy tải model vào cùng thư mục với file run_robot_ai.py."
    )

base_options = python.BaseOptions(model_asset_path=HAND_LANDMARKER_MODEL)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE,
    num_hands=1,
    min_hand_detection_confidence=0.8,
    min_hand_presence_confidence=0.8,
    min_tracking_confidence=0.8,
)
hand_landmarker = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)

try:
    while cap.isOpened():
        success, img = cap.read()
        if not success:
            break

        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        result = hand_landmarker.detect(mp_image)
    
        current_command = "WAITING..."
        stable_command = "WAITING..."
        confidence = 0.0

        if result.hand_landmarks:
            hand_landmarks = result.hand_landmarks[0]
            draw_hand_landmarks(img, hand_landmarks)

            wrist_x = hand_landmarks[0].x
            wrist_y = hand_landmarks[0].y

            row_data = []
            for lm in hand_landmarks:
                row_data.extend([lm.x - wrist_x, lm.y - wrist_y])

            # --- BỘ LỌC CHUẨN HÓA TỶ LỆ KHOẢNG CÁCH (NORMALIZATION) ---
            max_value = max(list(map(abs, row_data)))
            if max_value > 0:
                row_data = [n / max_value for n in row_data]

            input_data = np.array(row_data).reshape(1, -1)

            probabilities = model.predict_proba(input_data)[0]
            pred_index = int(np.argmax(probabilities))
            confidence = float(probabilities[pred_index])
            prediction = int(model.classes_[pred_index])

            if confidence < MIN_CONFIDENCE:
                current_command = "UNKNOWN"
            else:
                current_command = COMMAND_MAP.get(prediction, "UNKNOWN")

            # Đưa lệnh vừa nhận vào hàng đợi
            command_history.append(current_command)

            # Chỉ lấy lệnh xuất hiện nhiều nhất trong 5 frame gần nhất
            if len(command_history) == 5:
                stable_command = max(set(command_history), key=command_history.count)
            else:
                stable_command = current_command
        else:
            # Khi không có bàn tay nào trên màn hình -> Ép lệnh thành STOP
            stable_command = "STOP"
            command_history.clear()  # Nhạy hơn khi đưa tay vào lại
            
    # =====================================================================
    # ---> ĐOẠN CODE BẮN LỆNH QUA MQTT (Mới thêm vào) <---
    # Chỉ bắn đi nếu lệnh rõ ràng VÀ khác với lệnh vừa mới gửi trước đó
    # =====================================================================
        if stable_command not in ["UNKNOWN", "WAITING..."] and stable_command != last_sent_command:
            mqtt_client.publish(TOPIC, stable_command)
            print(f">> [MQTT] Đã bắn lệnh tới ESP32: {stable_command}")
            last_sent_command = stable_command

    # Hiển thị UI
        color = (0, 255, 0) if stable_command not in ["STOP", "UNKNOWN", "WAITING..."] else (0, 0, 255)
        cv2.putText(img, f'CMD: {stable_command}', (20, 50), cv2.FONT_HERSHEY_DUPLEX, 1.2, color, 2)
        cv2.putText(img, f'Conf: {confidence*100:.1f}%', (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        cv2.imshow("Artemis - AI Controller (Optimized)", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
except KeyboardInterrupt:
    print("Đã dừng bằng Ctrl+C.")
finally:
    cap.release()
    cv2.destroyAllWindows()
    with contextlib.suppress(BaseException):
        hand_landmarker.close()
    with contextlib.suppress(BaseException):
        mqtt_client.loop_stop()
        mqtt_client.disconnect()