import cv2
import mediapipe as mp
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
import joblib
import numpy as np
from collections import deque
import paho.mqtt.client as mqtt

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
model = joblib.load("gesture_model.pkl")

COMMAND_MAP = {
    0: "STOP",
    1: "FORWARD",
    2: "LEFT",
    3: "RIGHT",
    4: "BACKWARD",
    5: "BACK_LEFT",
    6: "BACK_RIGHT"  
}

# --- BỘ LỌC CHỐNG DỘI TÍN HIỆU (DEBOUNCE) ---
# Lưu tối đa 5 kết quả gần nhất
command_history = deque(maxlen=5) 

# 2. Cấu hình MediaPipe
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.8,
    min_tracking_confidence=0.8
)

cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, img = cap.read()
    if not success: break
        
    img = cv2.flip(img, 1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
    
    current_command = "WAITING..."
    stable_command = "WAITING..."
    confidence = 0.0
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            wrist_x = hand_landmarks.landmark[0].x
            wrist_y = hand_landmarks.landmark[0].y
            
            row_data = []
            for lm in hand_landmarks.landmark:
                row_data.extend([lm.x - wrist_x, lm.y - wrist_y])
            
            # --- BỘ LỌC CHUẨN HÓA TỶ LỆ KHOẢNG CÁCH (NORMALIZATION) ---
            max_value = max(list(map(abs, row_data)))
            if max_value > 0:
                row_data = [n / max_value for n in row_data]
                
            input_data = np.array(row_data).reshape(1, -1)
            
            probabilities = model.predict_proba(input_data)[0]
            confidence = np.max(probabilities)
            prediction = np.argmax(probabilities)
            
            if confidence < 0.75:
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
        command_history.clear() # Xóa lịch sử lệnh cũ để xe nhận lệnh mới nhạy hơn khi đưa tay vào lại
            
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
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()