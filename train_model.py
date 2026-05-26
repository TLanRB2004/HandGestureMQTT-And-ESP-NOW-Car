import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

try:
    from gesture_config import LABEL_TO_COMMAND
except Exception:
    LABEL_TO_COMMAND = {}

BASE_DIR = os.path.dirname(__file__)
CSV_FILE = os.path.join(BASE_DIR, "dataset_cuchi.csv")
MODEL_FILE = os.path.join(BASE_DIR, "gesture_model.pkl")

# 1. Đọc dữ liệu
print("Đang đọc dữ liệu từ file CSV...")
if not os.path.isfile(CSV_FILE):
    print(f"Không tìm thấy '{CSV_FILE}'. Hãy chạy hand_tracking.py để thu thập dữ liệu trước.")
    raise SystemExit(1)

df = pd.read_csv(CSV_FILE)
if df.empty:
    print(f"File '{CSV_FILE}' đang rỗng. Hãy thu thập dữ liệu rồi train lại.")
    raise SystemExit(1)

if "label" not in df.columns:
    print("CSV không đúng định dạng (thiếu cột 'label').")
    raise SystemExit(1)

df["label"] = df["label"].astype(int)
label_counts = df["label"].value_counts().sort_index()
print("Số mẫu theo nhãn:")
for label, count in label_counts.items():
    cmd_name = LABEL_TO_COMMAND.get(int(label), str(label))
    print(f"  {int(label)} ({cmd_name}): {int(count)}")

if LABEL_TO_COMMAND:
    missing_labels = sorted(set(LABEL_TO_COMMAND.keys()) - set(label_counts.index.tolist()))
    if missing_labels:
        print("CẢNH BÁO: Dataset đang thiếu mẫu cho các nhãn sau (nên thu thêm trước khi train):")
        for label in missing_labels:
            print(f"  {label} ({LABEL_TO_COMMAND.get(int(label), str(label))}): 0")

X = df.iloc[:, 1:].values  # Tọa độ
y = df["label"].values    # Nhãn lệnh

# --- BƯỚC SỬA LỖI: CHUẨN HÓA DỮ LIỆU ĐỒNG BỘ VỚI CAMERA ---
print("Đang chuẩn hóa (Normalize) tỷ lệ dữ liệu...")
X_normalized = []
for row in X:
    max_val = np.max(np.abs(row))
    if max_val > 0:
        X_normalized.append(row / max_val) # Chia cho giá trị lớn nhất
    else:
        X_normalized.append(row)
X_normalized = np.array(X_normalized)

# 2. Chia tập dữ liệu
try:
    X_train, X_test, y_train, y_test = train_test_split(
        X_normalized,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
except ValueError:
    # Nếu một số nhãn quá ít mẫu, stratify sẽ lỗi -> fallback
    X_train, X_test, y_train, y_test = train_test_split(
        X_normalized,
        y,
        test_size=0.2,
        random_state=42,
    )

# 3. Khởi tạo và Huấn luyện
print("Đang huấn luyện bộ não AI mới...")
model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1, class_weight="balanced")
model.fit(X_train, y_train)

# 4. Kiểm tra
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"-> Quá trình huấn luyện thành công!")
print(f"-> Độ chính xác của AI (Accuracy): {accuracy * 100:.2f}%")

# 5. Lưu mô hình
joblib.dump(model, MODEL_FILE)
print(f"Đã ghi đè bộ não AI MỚI vào file '{MODEL_FILE}'.")