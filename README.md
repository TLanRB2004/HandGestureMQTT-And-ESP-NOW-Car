# Hand Gesture MQTT And ESP-NOW Car

Repo này chỉ giữ 2 firmware cho xe:

1. `main.py`: firmware MicroPython
2. `esp32_cpp/ESP32_Gesture_Car.ino`: firmware C++ cho Arduino IDE

## MQTT local

- `MQTTX` trên máy tính có thể publish trực tiếp vào broker local bằng payload plain text như `STOP`, `FORWARD`, `LEFT`.
- Nếu broker chạy trên chính máy Windows của bạn, PC client có thể dùng `127.0.0.1:1883`.
- ESP32 không dùng `localhost`; hãy nhập IP LAN của máy chạy broker, ví dụ `192.168.1.20`.
- Cấu hình chi tiết Mosquitto: xem [README_Mosquitto.md](README_Mosquitto.md).

## MicroPython firmware

- File: [main.py](main.py)
- MQTT topic mặc định: `artemis/robot/command`
- WiFi và broker cần sửa trong đầu file `main.py`
- Thư viện MicroPython cần có: `network`, `machine`, `umqtt.simple`

## Arduino IDE C++ firmware

- File: [esp32_cpp/ESP32_Gesture_Car.ino](esp32_cpp/ESP32_Gesture_Car.ino)
- Cần cài thư viện `PubSubClient` và `ESP32Servo`
- Broker, WiFi và topic cũng cần sửa trong đầu file `.ino`

## MQTT payload hỗ trợ

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

## Chân phần cứng

| Thiết bị | GPIO |
|---|---|
| Servo | `18` |
| L298N `ENA` | `32` |
| L298N `IN1` | `26` |
| L298N `IN2` | `27` |
| L298N `IN3` | `14` |
| L298N `IN4` | `12` |
| L298N `ENB` | `13` |

## Lưu ý nhanh

- Nếu dùng MQTTX để test, hãy gửi payload dạng plain text, không phải JSON.
- Nếu broker chạy trên PC Windows của bạn, ESP32 phải nhập IP LAN của máy đó, không phải `localhost`.
