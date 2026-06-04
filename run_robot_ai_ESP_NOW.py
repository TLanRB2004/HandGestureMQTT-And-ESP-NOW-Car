import contextlib
import os
import time
from collections import deque

import cv2
import joblib
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import serial
from serial.tools import list_ports

from gesture_config import LABEL_TO_COMMAND

# Hand connections for indices 5-20
HAND_CONNECTIONS = [
    (5, 6), (6, 7), (7, 8),
    (9, 10), (10, 11), (11, 12),
    (13, 14), (14, 15), (15, 16),
    (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]

SERIAL_PORT = os.environ.get("SERIAL_PORT", "COM9").strip() or "COM3"
SERIAL_BAUD = int(os.environ.get("SERIAL_BAUD", "115200"))
SERIAL_WRITE_TIMEOUT = float(os.environ.get("SERIAL_WRITE_TIMEOUT", "1.0"))
SERIAL_OPEN_DELAY_S = float(os.environ.get("SERIAL_OPEN_DELAY_S", "2.0"))


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
    for i in range(5, 21):
        lm = hand_landmarks[i]
        cv2.circle(image, (int(lm.x * w), int(lm.y * h)), 4, (0, 0, 255), -1)


def open_serial():
    try:
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=SERIAL_BAUD,
            timeout=0.1,
            write_timeout=SERIAL_WRITE_TIMEOUT,
        )
    except serial.SerialException as exc:
        ports = ", ".join(p.device for p in list_ports.comports()) or "none"
        raise SystemExit(
            f"Cannot open serial port {SERIAL_PORT}. "
            f"Available ports: {ports}. "
            "Set SERIAL_PORT to the correct COM port."
        ) from exc

    time.sleep(SERIAL_OPEN_DELAY_S)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    return ser


def send_command(ser, command):
    payload = f"{command}\n".encode("utf-8")
    ser.write(payload)
    ser.flush()


last_sent_command = None

MODEL_FILE = os.path.join(os.path.dirname(__file__), "gesture_model.pkl")
if not os.path.isfile(MODEL_FILE):
    raise FileNotFoundError(
        "Missing 'gesture_model.pkl'. Run hand_tracking.py then train_model.py to create it."
    )
model = joblib.load(MODEL_FILE)

COMMAND_MAP = LABEL_TO_COMMAND
MIN_CONFIDENCE = 0.65

command_history = deque(maxlen=5)

HAND_LANDMARKER_MODEL = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
if not os.path.isfile(HAND_LANDMARKER_MODEL):
    raise FileNotFoundError(
        "Missing 'hand_landmarker.task'. Place it next to run_robot_ai_serial.py."
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

print(f"Using serial port {SERIAL_PORT} @ {SERIAL_BAUD} baud.")
serial_conn = open_serial()

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

            ref_x = hand_landmarks[5].x
            ref_y = hand_landmarks[5].y

            row_data = []
            for i in range(5, 21):
                lm = hand_landmarks[i]
                row_data.extend([lm.x - ref_x, lm.y - ref_y])

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

            command_history.append(current_command)

            if len(command_history) == 5:
                stable_command = max(set(command_history), key=command_history.count)
            else:
                stable_command = current_command
        else:
            stable_command = "STOP"
            command_history.clear()

        if stable_command not in ["UNKNOWN", "WAITING..."] and stable_command != last_sent_command:
            try:
                send_command(serial_conn, stable_command)
                print(f">> [SERIAL] Sent command: {stable_command}")
                last_sent_command = stable_command
            except serial.SerialException as exc:
                print(f"Serial send failed: {exc}")
                last_sent_command = None

        color = (0, 255, 0) if stable_command not in ["STOP", "UNKNOWN", "WAITING..."] else (0, 0, 255)
        cv2.putText(img, f"CMD: {stable_command}", (20, 50), cv2.FONT_HERSHEY_DUPLEX, 1.2, color, 2)
        cv2.putText(img, f"Conf: {confidence * 100:.1f}%", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        cv2.imshow("Artemis - AI Controller (Serial)", img)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
except KeyboardInterrupt:
    print("Stopped by Ctrl+C.")
finally:
    cap.release()
    cv2.destroyAllWindows()
    with contextlib.suppress(BaseException):
        hand_landmarker.close()
    with contextlib.suppress(BaseException):
        serial_conn.close()
