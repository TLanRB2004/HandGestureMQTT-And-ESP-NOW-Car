import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import csv
import os
import contextlib
import time

from gesture_config import KEY_TO_LABEL, LABEL_TO_COMMAND, QUIT_KEY

BASE_DIR = os.path.dirname(__file__)
csv_file = os.path.join(BASE_DIR, "dataset_cuchi.csv")

IMAGES_DIR = os.path.join(BASE_DIR, "dataset_images")
# Lưu ảnh khi đang ghi dataset (để xem lại sau).
# Nếu máy bị lag/ảnh quá nhiều, tăng IMAGE_SAVE_EVERY_N lên (vd: 2 hoặc 3).
SAVE_IMAGES = True
IMAGE_SAVE_EVERY_N = 1
SAVE_CROPPED_HAND = True
JPEG_QUALITY = 85


def crop_hand_region(image, hand_landmarks, margin_ratio=0.2):
    h, w, _ = image.shape
    xs = [lm.x for lm in hand_landmarks]
    ys = [lm.y for lm in hand_landmarks]

    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)

    box_w = max(x_max - x_min, 1e-6)
    box_h = max(y_max - y_min, 1e-6)

    x_min -= box_w * margin_ratio
    x_max += box_w * margin_ratio
    y_min -= box_h * margin_ratio
    y_max += box_h * margin_ratio

    x1 = max(int(x_min * w), 0)
    y1 = max(int(y_min * h), 0)
    x2 = min(int(x_max * w), w - 1)
    y2 = min(int(y_max * h), h - 1)

    if x2 <= x1 or y2 <= y1:
        return None
    return image[y1:y2, x1:x2]

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

# Tạo Header nếu file chưa tồn tại
if not os.path.isfile(csv_file) or os.stat(csv_file).st_size == 0:
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        header = ['label']
        for i in range(21):
            header.extend([f'x{i}', f'y{i}'])
        writer.writerow(header)

HAND_LANDMARKER_MODEL = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
if not os.path.isfile(HAND_LANDMARKER_MODEL):
    raise FileNotFoundError(
        "Thiếu file 'hand_landmarker.task'. Hãy tải model vào cùng thư mục với file hand_tracking.py."
    )

base_options = python.BaseOptions(model_asset_path=HAND_LANDMARKER_MODEL)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7,
)
hand_landmarker = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)

# BÍ QUYẾT CHỐNG LAG: Mở file 1 lần duy nhất ở đây và giữ nó luôn mở
f = open(csv_file, mode='a', newline='')
writer = csv.writer(f)

recorded_counts = {label: 0 for label in LABEL_TO_COMMAND}
saved_image_counts = {label: 0 for label in LABEL_TO_COMMAND}

print("--- HƯỚNG DẪN THU THẬP DATASET ---")
print(f"Lưu dữ liệu vào: {os.path.abspath(csv_file)}")
if SAVE_IMAGES:
    print(f"Lưu ảnh vào: {os.path.abspath(IMAGES_DIR)} (mỗi {IMAGE_SAVE_EVERY_N} mẫu)")
print("Giữ phím số để ghi dữ liệu:")
help_pairs = [
    f"{chr(key_code)}={LABEL_TO_COMMAND.get(label, str(label))}"
    for key_code, label in sorted(KEY_TO_LABEL.items(), key=lambda kv: kv[0])
]
print("  " + ", ".join(help_pairs))
print("Bấm [q] để thoát.")

try:
    while cap.isOpened():
        success, img = cap.read()
        if not success:
            break

        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        result = hand_landmarker.detect(mp_image)

        key = cv2.waitKey(1) & 0xFF

        if key == QUIT_KEY:
            break

        recording_label = KEY_TO_LABEL.get(key, -1)

        if result.hand_landmarks:
            hand_landmarks = result.hand_landmarks[0]
            draw_hand_landmarks(img, hand_landmarks)

            wrist_x = hand_landmarks[0].x
            wrist_y = hand_landmarks[0].y

            row_data = []
            for lm in hand_landmarks:
                row_data.extend([lm.x - wrist_x, lm.y - wrist_y])

            if recording_label != -1:
                row_data.insert(0, recording_label)
                writer.writerow(row_data)
                recorded_counts[recording_label] = recorded_counts.get(recording_label, 0) + 1

                cmd_name = LABEL_TO_COMMAND.get(recording_label, str(recording_label))

                if SAVE_IMAGES and (recorded_counts[recording_label] % IMAGE_SAVE_EVERY_N == 0):
                    label_dir = os.path.join(IMAGES_DIR, f"{recording_label:02d}_{cmd_name}")
                    os.makedirs(label_dir, exist_ok=True)

                    saved_image_counts[recording_label] = saved_image_counts.get(recording_label, 0) + 1
                    image_index = saved_image_counts[recording_label]
                    filename = f"{int(time.time() * 1000)}_{image_index:06d}.jpg"
                    out_path = os.path.join(label_dir, filename)

                    img_to_save = img
                    if SAVE_CROPPED_HAND:
                        cropped = crop_hand_region(img, hand_landmarks)
                        if cropped is not None:
                            img_to_save = cropped

                    cv2.imwrite(
                        out_path,
                        img_to_save,
                        [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
                    )

                cv2.putText(
                    img,
                    f'RECORDING: {recording_label} ({cmd_name}) | COUNT: {recorded_counts[recording_label]}',
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2,
                )
            else:
                cv2.putText(
                    img,
                    'Hold keys (0-9, a/s/d) to Record',
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 0, 0),
                    2,
                )

        cv2.imshow("Artemis - Data Collector", img)
finally:
    f.close()
    cap.release()
    cv2.destroyAllWindows()
    with contextlib.suppress(BaseException):
        hand_landmarker.close()

    total_written = sum(recorded_counts.values())
    print("\n--- TÓM TẮT THU THẬP DATASET ---")
    print(f"Tổng số mẫu ghi trong lần chạy này: {total_written}")
    print("Số mẫu theo nhãn (lần chạy này):")
    for label in sorted(recorded_counts.keys()):
        cmd_name = LABEL_TO_COMMAND.get(label, str(label))
        print(f"  {label} ({cmd_name}): {recorded_counts[label]}")
    if SAVE_IMAGES:
        total_images = sum(saved_image_counts.values())
        print(f"Tổng số ảnh đã lưu trong lần chạy này: {total_images}")
        print(f"Thư mục ảnh: {os.path.abspath(IMAGES_DIR)}")
    print(f"File CSV: {os.path.abspath(csv_file)}")