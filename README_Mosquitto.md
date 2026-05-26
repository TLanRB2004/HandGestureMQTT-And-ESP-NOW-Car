# Hướng dẫn Mosquitto

Tài liệu này dành riêng cho broker Mosquitto trên Windows khi bạn muốn:

- Python/MQTTX chạy trên cùng laptop
- ESP32/ESP8266 kết nối vào broker qua Wi-Fi trong LAN

## 1. Vấn đề thường gặp

Nếu Mosquitto chỉ lắng nghe ở `127.0.0.1:1883`, thì:

- `run_robot_ai.py` trên cùng máy vẫn kết nối được bằng `127.0.0.1`
- ESP32 sẽ không vào được bằng IP LAN của laptop

Muốn ESP32 kết nối được, Mosquitto phải lắng nghe trên `0.0.0.0` hoặc IP LAN của máy tính.

## 2. Cấu hình Mosquitto

Mở file cấu hình Mosquitto, ví dụ `mosquitto.conf`, rồi thêm:

```conf
listener 1883 0.0.0.0
allow_anonymous true
```

Nếu bạn muốn bật xác thực username/password thì dùng:

```conf
listener 1883 0.0.0.0
allow_anonymous false
password_file C:\mosquitto\passwordfile
```

## 3. Khởi động lại Mosquitto

Nếu chạy dạng service trên Windows:

```powershell
net stop mosquitto
net start mosquitto
```

Nếu chạy bằng tay từ terminal:

```powershell
mosquitto -v -c "C:\duongdan\mosquitto.conf"
```

## 4. Mở firewall

Nếu Windows Firewall chặn port 1883, mở inbound rule cho TCP 1883:

```powershell
New-NetFirewallRule -DisplayName "Mosquitto 1883" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow -Profile Private
```

## 5. Kiểm tra broker

Kiểm tra xem port 1883 có đang lắng nghe không:

```powershell
netstat -ano | findstr :1883
```

Test publish/subscribe ngay trên laptop:

```powershell
mosquitto_sub -h 127.0.0.1 -t artemis/robot/command -v
mosquitto_pub -h 127.0.0.1 -t artemis/robot/command -m STOP
```

Nếu ESP32 ở cùng mạng Wi-Fi, hãy lấy IP LAN của laptop bằng `ipconfig` và nhập IP đó vào firmware ESP32.

## 6. Cách dùng với project này

- `run_robot_ai.py` mặc định dùng `127.0.0.1:1883` cho broker local trên chính máy chạy Python.
- `main.py` và `esp32_cpp/ESP32_Gesture_Car.ino` phải dùng IP LAN của laptop, không dùng `localhost`.
- Topic mặc định của project là `artemis/robot/command`.
- Payload phải là plain text như `STOP`, `FORWARD`, `LEFT`, `RIGHT`.