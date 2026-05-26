import network
import time
from umqtt.simple import MQTTClient
from machine import Pin, PWM

# --- CẤU HÌNH WIFI & MQTT ---
WIFI_SSID = "TEN_WIFI_CUA_BAN"
WIFI_PASS = "MAT_KHAU_WIFI_CUA_BAN"

# IP của máy đang chạy MQTT broker local trong mạng LAN.
# Không dùng localhost vì ESP32 phải kết nối tới máy tính thật.
BROKER = "192.168.1.100"
CLIENT_ID = "esp32_artemis_car_servo"
TOPIC = b"artemis/robot/command" 

# --- CẤU HÌNH SERVO MG90S ---
servo = PWM(Pin(18), freq=50)

ANGLE_STRAIGHT = 90
ANGLE_LEFT = 120    
ANGLE_RIGHT = 60

# Biến toàn cục để nhớ vị trí bánh xe hiện tại
current_angle = ANGLE_STRAIGHT 

# ---> HÀM BẺ LÁI MƯỢT (SMOOTH SERVO) <---
def smooth_servo(target_angle):
    global current_angle
    # Nếu góc đã đúng rồi thì bỏ qua
    if current_angle == target_angle:
        return
        
    # Tính bước nhảy (tăng hoặc giảm)
    step = 1 if target_angle > current_angle else -1
    
    # Chạy vòng lặp bẻ từng độ một
    for angle in range(current_angle, target_angle + step, step):
        min_duty = 40
        max_duty = 115
        duty = int(min_duty + (angle / 180) * (max_duty - min_duty))
        servo.duty(duty)
        # THAY ĐỔI ĐỘ MƯỢT TẠI ĐÂY:
        # Tăng số này lên (vd: 0.02) thì servo xoay càng chậm và êm
        time.sleep(0.01) 
        
    # Cập nhật lại vị trí hiện tại
    current_angle = target_angle

# --- CẤU HÌNH L298N ---
ena = PWM(Pin(32), freq=1000) 
in1 = Pin(26, Pin.OUT)
in2 = Pin(27, Pin.OUT)
in3 = Pin(14, Pin.OUT)
in4 = Pin(12, Pin.OUT)
enb = PWM(Pin(13), freq=1000)

CAR_SPEED_NORMAL = 600
CAR_SPEED_SLOW = 350

def set_speed(speed):
    ena.duty(speed)
    enb.duty(speed)

set_speed(CAR_SPEED_NORMAL)

def drive_forward():
    in1.value(0); in2.value(1)
    in3.value(0); in4.value(1)

def drive_backward():
    in1.value(1); in2.value(0)
    in3.value(1); in4.value(0)

def stop_car():
    in1.value(0); in2.value(0)
    in3.value(0); in4.value(0)

# --- HÀM XỬ LÝ LỆNH TỪ AI ---
def mqtt_callback(topic, msg):
    command_raw = msg.decode('utf-8')
    print("ESP32 nhận lệnh:", command_raw)

    is_slow = False
    command = command_raw
    if command_raw.endswith("_SLOW"):
        is_slow = True
        command = command_raw[:-5]  # bỏ "_SLOW"
    
    # TỐI ƯU TRÌNH TỰ: Luôn khóa 2 bánh sau lại trước khi chuyển hướng
    stop_car() 

    # Chỉnh tốc độ theo lệnh (SLOW / NORMAL)
    set_speed(CAR_SPEED_SLOW if is_slow else CAR_SPEED_NORMAL)
    
    if command == "FORWARD":
        smooth_servo(ANGLE_STRAIGHT) # Trả lái từ từ về thẳng
        drive_forward()              # Rồi mới đẩy tới
        
    elif command == "BACKWARD":
        smooth_servo(ANGLE_STRAIGHT)
        drive_backward()             
        
    elif command == "LEFT":
        smooth_servo(ANGLE_LEFT)     # Bẻ từ từ sang trái
        drive_forward()              # Bẻ xong mới truyền động đẩy xe đi
        
    elif command == "RIGHT":
        smooth_servo(ANGLE_RIGHT)    
        drive_forward()
        
    elif command == "BACK_LEFT":
        smooth_servo(ANGLE_LEFT)     # Bẻ lái trái
        drive_backward()             # Bánh sau kéo lùi
        
    elif command == "BACK_RIGHT":
        smooth_servo(ANGLE_RIGHT)    # Bẻ lái phải
        drive_backward()             # Bánh sau kéo lùi    
        
    elif command == "STOP":
        smooth_servo(ANGLE_STRAIGHT) # Trả bánh thẳng thớm cất xe 
        # (Không cần gọi stop_car nữa vì đã ngắt ở trên cùng rồi)

# --- KẾT NỐI WIFI ---
print("Đang kết nối WiFi...")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)
while not wlan.isconnected():
    time.sleep(0.5)
print("WiFi OK! IP:", wlan.ifconfig()[0])

# --- KẾT NỐI MQTT ---
client = MQTTClient(CLIENT_ID, BROKER)
client.set_callback(mqtt_callback)
client.connect()
client.subscribe(TOPIC)
print("Đã đăng ký kênh MQTT. Chờ lệnh điều khiển...")

# Reset hệ thống
set_servo_angle = smooth_servo # Ánh xạ hàm cũ cho khởi tạo
smooth_servo(ANGLE_STRAIGHT)
stop_car() 

# --- VÒNG LẶP CHÍNH ---
try:
    while True:
        client.check_msg()
        time.sleep(0.01)
except KeyboardInterrupt:
    print("Ngắt kết nối!")
    stop_car()
    client.disconnect()
