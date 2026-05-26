# Hand Gesture MQTT And ESP-NOW Car

Dự án điều khiển xe bằng cử chỉ tay qua webcam, huấn luyện mô hình từ dữ liệu landmark và gửi lệnh qua MQTT đến ESP32/ESP8266 chạy MicroPython.

## 1. Tổng quan

Luồng hoạt động của dự án:

1. `hand_tracking.py` thu thập dữ liệu cử chỉ tay và lưu vào `dataset_cuchi.csv`.
2. `train_model.py` huấn luyện mô hình Random Forest và tạo `gesture_model.pkl`.
3. `run_robot_ai.py` nhận diện cử chỉ theo thời gian thực, hiển thị kết quả và gửi lệnh MQTT.
4. `main.py` là firmware MicroPython trên ESP32 để nhận lệnh MQTT và điều khiển xe.
5. `preview_dataset.py` tạo ảnh xem trước landmark từ file CSV.

## 2. Cấu trúc chính

- `gesture_config.py`: ánh xạ giữa nhãn số và lệnh điều khiển.
- `hand_tracking.py`: thu thập dataset bằng webcam.
- `train_model.py`: huấn luyện mô hình nhận diện cử chỉ.
- `run_robot_ai.py`: chạy AI, lọc tín hiệu và bắn lệnh MQTT.
- `main.py`: code MicroPython cho ESP32.
- `hand_landmarker.task`: model Hand Landmarker của MediaPipe.
- `dataset_cuchi.csv`: dữ liệu landmark đã thu.
- `gesture_model.pkl`: mô hình đã huấn luyện.

## 3. Yêu cầu môi trường

Khuyến nghị dùng:

- Python 3.10 hoặc 3.11, bản 64-bit.
- Webcam hoạt động tốt.
- ESP32/ESP8266 chạy MicroPython.
- Kết nối Internet để cài thư viện Python.

### Thư viện Python cần cài

Các gói ở `requirements.txt`:

- `opencv-python`
- `mediapipe`
- `numpy`
- `pandas`
- `scikit-learn`
- `joblib`
- `paho-mqtt`

Lưu ý: `network`, `machine`, `umqtt.simple` là thư viện của MicroPython trên board, không cài bằng `pip` trên máy tính.

## 4. Cài đặt trên máy tính

Mở PowerShell tại thư mục `Source Code` rồi chạy:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu máy đã có sẵn `.venv` thì chỉ cần kích hoạt môi trường rồi cài thư viện.

## 5. Cách chạy từng phần

### 5.1. Thu thập dữ liệu cử chỉ

Chạy:

```powershell
python hand_tracking.py
```

Trong lúc thu dữ liệu:

| Phím | Lệnh |
|---|---|
| `0` | `STOP` |
| `1` | `FORWARD` |
| `2` | `LEFT` |
| `3` | `RIGHT` |
| `4` | `BACKWARD` |
| `5` | `BACK_LEFT` |
| `6` | `BACK_RIGHT` |
| `7` | `FORWARD_SLOW` |
| `8` | `LEFT_SLOW` |
| `9` | `RIGHT_SLOW` |
| `a` | `BACKWARD_SLOW` |
| `s` | `BACK_LEFT_SLOW` |
| `d` | `BACK_RIGHT_SLOW` |
| `q` | Thoát |

File sẽ ghi dữ liệu vào `dataset_cuchi.csv` và lưu ảnh kiểm tra trong `dataset_images/`.

### 5.2. Huấn luyện mô hình

Sau khi có dữ liệu, chạy:

```powershell
python train_model.py
```

Kết quả:

- Đọc dữ liệu từ `dataset_cuchi.csv`.
- Huấn luyện mô hình Random Forest.
- Ghi mô hình ra `gesture_model.pkl`.

### 5.3. Xem trước dataset landmark

Nếu muốn xuất ảnh preview từ CSV, chạy:

```powershell
python preview_dataset.py
```

Ảnh sẽ được tạo trong `dataset_landmark_preview/`.

### 5.4. Chạy nhận diện cử chỉ và gửi lệnh MQTT

Chạy:

```powershell
python run_robot_ai.py
```

Chương trình sẽ:

1. Mở webcam.
2. Nhận diện 21 điểm tay bằng MediaPipe.
3. Dự đoán cử chỉ bằng `gesture_model.pkl`.
4. Gửi lệnh MQTT tới topic `artemis/robot/command`.

Broker và topic mặc định trong code:

- Broker: `broker.emqx.io`
- Port: `1883`
- Topic: `artemis/robot/command`

## 6. Nạp code lên ESP32 / ESP8266

File `main.py` là chương trình MicroPython, nên bạn cần copy file này vào board dưới tên `main.py`.

Trước khi nạp, hãy sửa các thông số sau trong `main.py`:

- `WIFI_SSID`
- `WIFI_PASS`
- Nếu cần, chỉnh `BROKER`, `CLIENT_ID`, `TOPIC`

Pin phần cứng theo code hiện tại:

| Thiết bị | GPIO |
|---|---|
| Servo | `18` |
| L298N `ENA` | `32` |
| L298N `IN1` | `26` |
| L298N `IN2` | `27` |
| L298N `IN3` | `14` |
| L298N `IN4` | `12` |
| L298N `ENB` | `13` |

Khi board chạy, nó sẽ kết nối WiFi, subscribe topic MQTT và nhận lệnh điều khiển xe.

### Thư viện MicroPython cần có trên board

- `umqtt.simple`
- `network`
- `machine`

Nếu board chưa có `umqtt.simple`, bạn cần upload file tương ứng từ `micropython-lib` hoặc cài bằng công cụ bạn đang dùng để nạp firmware.

## 7. Ghi chú quan trọng

- `hand_landmarker.task` phải nằm cùng thư mục với các file Python chạy trên PC.
- `gesture_model.pkl` phải tồn tại thì `run_robot_ai.py` mới chạy được.
- `dataset_cuchi.csv` là file dữ liệu đầu vào cho `train_model.py`.
- Nếu muốn train lại từ đầu, nên thu thêm dữ liệu rồi chạy lại `train_model.py`.

## 8. Xử lý lỗi thường gặp

### Không mở được webcam

- Kiểm tra webcam đã được ứng dụng khác sử dụng chưa.
- Thử đổi chỉ số `cv2.VideoCapture(0)` nếu máy có nhiều camera.

### Không tìm thấy `hand_landmarker.task`

- Đảm bảo file nằm trong cùng thư mục với script Python.

### Không kết nối được MQTT

- Kiểm tra Internet.
- Kiểm tra broker `broker.emqx.io` còn hoạt động.
- Xác nhận topic giữa máy tính và ESP32 giống nhau.

### Board không nhận lệnh

- Kiểm tra WiFi đã kết nối thành công chưa.
- Kiểm tra `WIFI_SSID`, `WIFI_PASS` và topic MQTT.
- Kiểm tra dây nối servo, L298N và nguồn cấp.

## 9. Gợi ý quy trình chạy nhanh

1. Cài thư viện Python.
2. Chạy `hand_tracking.py` để thu dataset.
3. Chạy `train_model.py` để tạo model.
4. Chạy `run_robot_ai.py` để test điều khiển qua MQTT.
5. Nạp `main.py` lên ESP32 để xe nhận lệnh.