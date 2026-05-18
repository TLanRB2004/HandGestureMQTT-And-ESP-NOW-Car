import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

# 1. Đọc dữ liệu
print("Đang đọc dữ liệu từ file CSV...")
df = pd.read_csv("dataset_cuchi.csv")

X = df.iloc[:, 1:].values  # Tọa độ
y = df.iloc[:, 0].values   # Nhãn lệnh

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
X_train, X_test, y_train, y_test = train_test_split(X_normalized, y, test_size=0.2, random_state=42)

# 3. Khởi tạo và Huấn luyện
print("Đang huấn luyện bộ não AI mới...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 4. Kiểm tra
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"-> Quá trình huấn luyện thành công!")
print(f"-> Độ chính xác của AI (Accuracy): {accuracy * 100:.2f}%")

# 5. Lưu mô hình
joblib.dump(model, "gesture_model.pkl")
print("Đã ghi đè bộ não AI MỚI vào file 'gesture_model.pkl'.")