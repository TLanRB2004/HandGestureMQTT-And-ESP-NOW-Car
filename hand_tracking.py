import cv2
import mediapipe as mp
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
import csv
import os

csv_file = "dataset_cuchi.csv"

# Tạo Header nếu file chưa tồn tại
if not os.path.isfile(csv_file) or os.stat(csv_file).st_size == 0:
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        header = ['label']
        for i in range(21):
            header.extend([f'x{i}', f'y{i}'])
        writer.writerow(header)

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

cap = cv2.VideoCapture(0)

# BÍ QUYẾT CHỐNG LAG: Mở file 1 lần duy nhất ở đây và giữ nó luôn mở
f = open(csv_file, mode='a', newline='')
writer = csv.writer(f)

print("--- HƯỚNG DẪN THU THẬP DATASET ---")
print("Bấm và GIỮ các phím số: 0 (Dừng), 1 (Tiến), 2 (Trái), 3 (Phải), 4 (Lùi), 5(Lùi Trái), 6(Lùi Phải)")
print("Bấm [q] để thoát.")

while cap.isOpened():
    success, img = cap.read()
    if not success:
        break
        
    img = cv2.flip(img, 1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
    
    key = cv2.waitKey(1) & 0xFF
    
    recording_label = -1
    if key == ord('0'): recording_label = 0
    elif key == ord('1'): recording_label = 1
    elif key == ord('2'): recording_label = 2
    elif key == ord('3'): recording_label = 3
    elif key == ord('4'): recording_label = 4
    elif key == ord('5'): recording_label = 5
    elif key == ord('6'): recording_label = 6
    elif key == ord('q'): break

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            wrist_x = hand_landmarks.landmark[0].x
            wrist_y = hand_landmarks.landmark[0].y
            
            row_data = []
            for lm in hand_landmarks.landmark:
                # Tính tọa độ tương đối và nạp thẳng vào mảng
                row_data.extend([lm.x - wrist_x, lm.y - wrist_y])
                
            if recording_label != -1:
                row_data.insert(0, recording_label)
                # Ghi thẳng vào file đang mở (Tốc độ siêu nhanh, không lag)
                writer.writerow(row_data)
                
                cv2.putText(img, f'RECORDING: LABEL {recording_label}', (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                cv2.putText(img, 'Press 0, 1, 2, 3, 4, 5, 6 to Record', (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    cv2.imshow("Artemis - Data Collector", img)

# Bắt buộc: Đóng file lại khi kết thúc chương trình để lưu dữ liệu an toàn
f.close()
cap.release()
cv2.destroyAllWindows()