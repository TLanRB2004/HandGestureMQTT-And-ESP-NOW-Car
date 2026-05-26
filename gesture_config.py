# Cấu hình nhãn (label) và lệnh (command) dùng chung cho:
# - hand_tracking.py (thu thập dataset)
# - train_model.py (train model)
# - run_robot_ai.py (nhận diện + bắn MQTT)

# Numeric labels stored in dataset_cuchi.csv
LABEL_TO_COMMAND = {
    0: "STOP",
    1: "FORWARD",
    2: "LEFT",
    3: "RIGHT",
    4: "BACKWARD",
    5: "BACK_LEFT",
    6: "BACK_RIGHT",

    # Slow variants
    7: "FORWARD_SLOW",
    8: "LEFT_SLOW",
    9: "RIGHT_SLOW",
    10: "BACKWARD_SLOW",
    11: "BACK_LEFT_SLOW",
    12: "BACK_RIGHT_SLOW",
}

# Key mapping for recording in hand_tracking.py (cv2.waitKey)
# 0-9 are digits; a/s/d are extra keys for slow backward variants.
KEY_TO_LABEL = {
    ord('0'): 0,
    ord('1'): 1,
    ord('2'): 2,
    ord('3'): 3,
    ord('4'): 4,
    ord('5'): 5,
    ord('6'): 6,
    ord('7'): 7,
    ord('8'): 8,
    ord('9'): 9,
    ord('a'): 10,
    ord('s'): 11,
    ord('d'): 12,
}

QUIT_KEY = ord('q')
