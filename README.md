# Hand Gesture MQTT And ESP-NOW Car

Dự án này dùng webcam để thu landmark bàn tay, train model nhận diện cử chỉ, sau đó gửi lệnh điều khiển xe qua MQTT tới ESP32. Repo hiện giữ 2 firmware chính:

- `main.py`: firmware MicroPython
- `esp32_cpp/ESP32_Gesture_Car.ino`: firmware C++ cho Arduino IDE

## 1. Cấu trúc thư mục

- `hand_tracking.py`: thu dữ liệu cử chỉ tay, lưu CSV và ảnh dataset
- `train_model.py`: train mô hình Random Forest từ file CSV
- `preview_dataset.py`: xuất ảnh xem trước landmark từ CSV
- `run_robot_ai.py`: nhận diện cử chỉ theo thời gian thực và publish MQTT
- `main.py`: firmware MicroPython cho ESP32
- `esp32_cpp/ESP32_Gesture_Car.ino`: firmware C++ cho Arduino IDE
- `gesture_config.py`: ánh xạ nhãn số sang tên lệnh
- `hand_landmarker.task`: model Hand Landmarker của MediaPipe
- `dataset_cuchi.csv`: dataset landmark đã thu
- `gesture_model.pkl`: model sau khi train
- `dataset_images/`: ảnh lưu trong lúc tracking
- `dataset_landmark_preview/`: ảnh preview landmark

## 2. Yêu cầu môi trường

### Trên máy tính

- Windows 10/11
- Python 3.10 hoặc 3.11, bản 64-bit
- Webcam hoạt động tốt
- Kết nối Internet để cài thư viện Python
- Mosquitto hoặc broker MQTT local
- MQTTX để test nếu muốn

### Thư viện Python

Các gói trong `requirements.txt`:

- `opencv-python`
- `mediapipe`
- `numpy`
- `pandas`
- `scikit-learn`
- `joblib`
- `paho-mqtt`

### Trên ESP32

- Nếu dùng MicroPython: cần `network`, `machine`, `umqtt.simple`
- Nếu dùng Arduino IDE: cần board package `esp32`, thư viện `PubSubClient` và `ESP32Servo`

## 3. Cài đặt môi trường Python

Mở PowerShell trong thư mục `Source Code` rồi chạy:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu bạn đã có sẵn `.venv` thì chỉ cần kích hoạt lại môi trường và cài thư viện.

## 4. Cách tracking / thu dataset

### 4.1. Chuẩn bị trước khi thu

Đặt `hand_landmarker.task` cùng thư mục với `hand_tracking.py`.

Kiểm tra camera hoạt động và đóng các ứng dụng khác đang giữ webcam nếu có.

### 4.2. Chạy chương trình tracking

```powershell
python hand_tracking.py
```

Chương trình sẽ:

- mở webcam
- detect 21 điểm tay bằng MediaPipe
- hiển thị khung hình live
- lưu dữ liệu vào `dataset_cuchi.csv`
- lưu ảnh vào `dataset_images/`

### 4.3. Phím ghi dữ liệu

Giữ các phím sau khi có bàn tay trong khung hình để ghi mẫu:

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

### 4.4. Dữ liệu được lưu như thế nào

- CSV lưu theo format: `label, x0, y0, x1, y1, ..., x20, y20`
- Ảnh được lưu theo thư mục: `dataset_images/<label>_<command>/`
- Ảnh thường được crop vùng bàn tay để dễ xem lại

### 4.5. Mẹo khi thu dataset

- Nên thu nhiều mẫu cho từng lớp, tránh lệch lớp quá nặng
- Giữ tay ở nhiều góc độ, độ cao và khoảng cách khác nhau
- Thu cả lớp `STOP` để model học được trạng thái không ra lệnh
- Nếu dữ liệu ít, model sẽ dễ nhầm giữa các lớp giống nhau

## 5. Xem trước dataset landmark

Nếu muốn xuất ảnh preview từ file CSV để kiểm tra trực quan:

```powershell
python preview_dataset.py
```

Kết quả sẽ nằm trong `dataset_landmark_preview/`.

## 6. Train model

### 6.1. Chạy train

Sau khi đã có dataset, chạy:

```powershell
python train_model.py
```

### 6.2. Script train làm gì

- đọc `dataset_cuchi.csv`
- kiểm tra cột `label`
- in số mẫu theo nhãn
- chuẩn hóa từng hàng dữ liệu theo độ lớn lớn nhất của hàng đó
- chia train/test với tỷ lệ 80/20
- train `RandomForestClassifier`
- đánh giá accuracy
- lưu model ra `gesture_model.pkl`

### 6.3. Lưu ý khi train

- Nếu CSV rỗng hoặc thiếu cột `label`, script sẽ dừng
- Nếu một số nhãn quá ít mẫu, phần `stratify` có thể lỗi và script sẽ tự fallback
- Nếu thiếu mẫu cho một số nhãn, model có thể nhận diện kém ở những nhãn đó

## 7. Chạy nhận diện cử chỉ và publish MQTT

### 7.1. Chạy script

```powershell
python run_robot_ai.py
```

### 7.2. Script này làm gì

- mở webcam
- detect landmark bàn tay bằng MediaPipe Hand Landmarker
- chuẩn hóa tọa độ tay giống lúc train
- đưa vào model `gesture_model.pkl`
- lấy lệnh có độ tin cậy cao nhất
- lọc chống dội tín hiệu bằng deque 5 frame
- publish lệnh MQTT dưới dạng plain text

### 7.3. MQTT topic và payload

- Topic mặc định: `artemis/robot/command`
- Payload là text đơn giản, ví dụ: `STOP`, `FORWARD`, `LEFT`, `RIGHT`
- Không gửi JSON nếu bạn đang test xe theo workflow này

### 7.4. Cấu hình broker cho `run_robot_ai.py`

Script hiện đọc biến môi trường, mặc định là broker local trên chính máy chạy Python:

- `MQTT_BROKER` mặc định: `127.0.0.1`
- `MQTT_PORT` mặc định: `1883`
- `MQTT_TOPIC` mặc định: `artemis/robot/command`

Ví dụ ép cấu hình trong PowerShell:

```powershell
$env:MQTT_BROKER="127.0.0.1"
$env:MQTT_PORT="1883"
$env:MQTT_TOPIC="artemis/robot/command"
python run_robot_ai.py
```

Nếu bạn muốn ESP32 ở cùng mạng Wi-Fi nhận lệnh, broker phải lắng nghe trên IP LAN hoặc `0.0.0.0`, không chỉ `127.0.0.1`.

## 8. MQTT và Mosquitto

### 8.1. Hiểu đúng localhost và LAN IP

- `127.0.0.1` chỉ dùng cho chính máy đang chạy broker
- IP LAN như `192.168.88.106` dùng cho thiết bị khác trong cùng mạng Wi-Fi
- ESP32 không bao giờ dùng `localhost`

### 8.2. Cấu hình Mosquitto để nghe trên LAN

Mở file `mosquitto.conf` và thêm tối thiểu:

```conf
listener 1883 0.0.0.0
allow_anonymous true
```

Nếu muốn bật xác thực username/password thì dùng:

```conf
listener 1883 0.0.0.0
allow_anonymous false
password_file C:\mosquitto\passwordfile
```

### 8.3. Khởi động lại Mosquitto

Nếu Mosquitto chạy dạng service trên Windows:

```powershell
net stop mosquitto
net start mosquitto
```

Nếu chạy bằng tay từ terminal:

```powershell
mosquitto -v -c "C:\duongdan\mosquitto.conf"
```

### 8.4. Mở firewall

Nếu Windows Firewall chặn port 1883, thêm rule inbound cho TCP 1883:

```powershell
New-NetFirewallRule -DisplayName "Mosquitto 1883" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow -Profile Private
```

### 8.5. Kiểm tra broker có nghe chưa

Kiểm tra port 1883:

```powershell
netstat -ano | findstr :1883
```

Nếu broker đã bật đúng, bạn sẽ thấy trạng thái `LISTENING`.

### 8.6. Test bằng mosquitto_pub / mosquitto_sub

Subscribe trên topic:

```powershell
mosquitto_sub -h 127.0.0.1 -t artemis/robot/command -v
```

Publish test:

```powershell
mosquitto_pub -h 127.0.0.1 -t artemis/robot/command -m STOP
```

Nếu bạn test từ máy khác trong LAN thì thay `127.0.0.1` bằng IP LAN của máy đang chạy broker.

### 8.7. Test bằng MQTTX

Trong MQTTX:

1. Tạo connection tới broker
2. Host là `127.0.0.1` nếu test trên chính laptop
3. Host là IP LAN nếu test từ máy khác
4. Port là `1883`
5. Topic là `artemis/robot/command`
6. Payload chọn dạng plain text
7. Gửi các lệnh như `STOP`, `FORWARD`, `LEFT`, `RIGHT`

## 9. Firmware MicroPython cho ESP32

File: [main.py](main.py)

### 9.1. Chức năng

Firmware MicroPython sẽ:

- kết nối Wi-Fi
- kết nối MQTT broker
- subscribe topic `artemis/robot/command`
- xử lý lệnh nhận được để điều khiển servo và motor

### 9.2. Cần sửa gì trước khi nạp

Sửa các biến sau trong đầu file `main.py`:

- `WIFI_SSID`
- `WIFI_PASS`
- `BROKER`
- `CLIENT_ID`
- `TOPIC`

Nếu broker chạy trên máy tính của bạn, `BROKER` phải là IP LAN của máy đó, không phải `localhost`.

### 9.3. Pin phần cứng hiện tại

| Thiết bị | GPIO |
|---|---|
| Servo | `18` |
| L298N `ENA` | `32` |
| L298N `IN1` | `26` |
| L298N `IN2` | `27` |
| L298N `IN3` | `14` |
| L298N `IN4` | `12` |
| L298N `ENB` | `13` |
| HC-SR04 `TRIG` | `19` |
| HC-SR04 `ECHO` | `21` |

### 9.4. Cảm biến HC-SR04 và tránh vật cản

- Nếu phát hiện vật cản gần (mặc định 20 cm), servo sẽ về thẳng 90 độ và xe lùi một chút.
- Ngưỡng khoảng cách và thời gian lùi có thể chỉnh trong code:
	- MicroPython: `OBSTACLE_CM`, `REVERSE_MS` trong [main.py](main.py)
	- Arduino IDE: `OBSTACLE_CM`, `REVERSE_MS` trong [esp32_cpp/ESP32_Gesture_Car.ino](esp32_cpp/ESP32_Gesture_Car.ino)
- Echo pin dùng interrupt để đo độ rộng xung chính xác hơn.

## 10. Firmware C++ cho Arduino IDE

File: [esp32_cpp/ESP32_Gesture_Car.ino](esp32_cpp/ESP32_Gesture_Car.ino)

### 10.1. Cần cài gì trong Arduino IDE

- Board package `esp32` của Espressif
- `PubSubClient`
- `ESP32Servo`

### 10.2. Cách nạp

1. Mở Arduino IDE
2. Cài board ESP32 nếu máy chưa có
3. Cài `PubSubClient` và `ESP32Servo`
4. Mở file `.ino`
5. Sửa `WIFI_SSID`, `WIFI_PASS`, `MQTT_BROKER_IP`, `MQTT_TOPIC` nếu cần
6. Chọn đúng board và COM port
7. Bấm Upload

### 10.3. Chức năng

- kết nối Wi-Fi
- kết nối MQTT
- subscribe topic `artemis/robot/command`
- nhận các lệnh plain text giống firmware MicroPython
- điều khiển servo và motor theo lệnh

## 11. Các lệnh MQTT được hỗ trợ

- `STOP`
- `FORWARD`
- `LEFT`
- `RIGHT`
- `BACKWARD`
- `BACK_LEFT`
- `BACK_RIGHT`
- `FORWARD_SLOW`
- `LEFT_SLOW`
- `RIGHT_SLOW`
- `BACKWARD_SLOW`
- `BACK_LEFT_SLOW`
- `BACK_RIGHT_SLOW`

## 12. Quy trình chạy nhanh từ đầu đến cuối

1. Cài thư viện Python
2. Cắm webcam và thu dataset bằng `hand_tracking.py`
3. Kiểm tra preview bằng `preview_dataset.py` nếu cần
4. Train model bằng `train_model.py`
5. Chạy Mosquitto local và mở port 1883 nếu cần
6. Chạy `run_robot_ai.py`
7. Test bằng MQTTX hoặc `mosquitto_pub`
8. Nạp `main.py` lên ESP32 hoặc dùng bản Arduino IDE C++

## 13. Lỗi thường gặp

### Không kết nối được MQTT

- Kiểm tra broker có đang chạy không
- Nếu cùng máy, dùng `127.0.0.1`
- Nếu ESP32 kết nối qua Wi-Fi, broker phải nghe trên LAN IP hoặc `0.0.0.0`
- Kiểm tra firewall port 1883

### `ConnectionRefusedError: WinError 10061`

- Thường là broker chưa mở port 1883 ở IP bạn nhập
- Nếu `netstat` chỉ thấy `127.0.0.1:1883 LISTENING`, ESP32 sẽ không vào được bằng IP LAN

### Không mở được webcam

- Đóng app khác đang chiếm camera
- Thử đổi index `cv2.VideoCapture(0)` nếu máy có nhiều camera

### Thiếu `hand_landmarker.task`

- Đặt file này cùng thư mục với script Python

### Thiếu `gesture_model.pkl`

- Chạy `train_model.py` lại sau khi có `dataset_cuchi.csv`

### ESP32 không nhận lệnh

- Kiểm tra SSID và mật khẩu Wi-Fi
- Kiểm tra broker IP
- Kiểm tra topic có trùng nhau không
- Kiểm tra dây servo, L298N và nguồn cấp

## 14. Ghi chú cuối

- Nếu bạn chỉ test trên laptop, `run_robot_ai.py` có thể dùng `127.0.0.1:1883`
- Nếu bạn muốn ESP32 nhận lệnh qua Wi-Fi, Mosquitto phải cấu hình để lắng nghe trên LAN
- Payload MQTT nên để dạng text đơn giản, không dùng JSON cho luồng này
