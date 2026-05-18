import network
import time
from umqtt.simple import MQTTClient
from machine import Pin, PWM

# --- CẤU HÌNH WIFI & MQTT ---
WIFI_SSID = "34 Nguyen Tao 2g" 
WIFI_PASS = "0905344352"

BROKER = "broker.emqx.io"
CLIENT_ID = "esp32_artemis_car_servo"
TOPIC = b"artemis/robot/command" 

# --- CẤU HÌNH SERVO MG90S (Đã đổi sang chân 19) ---
servo = PWM(Pin(18), freq=50)

# Các mốc góc bẻ lái
ANGLE_STRAIGHT = 90
ANGLE_LEFT = 130   
ANGLE_RIGHT = 50 

def set_servo_angle(angle):
    # Ép góc (0-180 độ) sang Duty Cycle (40-115) cho xung PWM 50Hz
    min_duty = 40
    max_duty = 115
    duty = int(min_duty + (angle / 180) * (max_duty - min_duty))
    servo.duty(duty)

# --- CẤU HÌNH L298N (Cập nhật chân PWM để giảm tốc) ---
# ENA, IN1, IN2, IN3, IN4, ENB -> 25, 26, 27, 14, 12, 13
ena = PWM(Pin(25), freq=1000) # Đổi sang dùng PWM với tần số 1000Hz
in1 = Pin(26, Pin.OUT)
in2 = Pin(27, Pin.OUT)
in3 = Pin(14, Pin.OUT)
in4 = Pin(12, Pin.OUT)
enb = PWM(Pin(13), freq=1000) # Đổi sang dùng PWM

# ==========================================
# BIẾN CHỈNH TỐC ĐỘ XE (Từ 0 đến 1023)
# 1023 là max ga, 0 là dừng. 
# Anh em cứ set tầm 500 - 700 là xe đi tà tà cực êm và dễ bẻ lái.
# ==========================================
CAR_SPEED = 300  

# Cấp xung tốc độ cho 2 động cơ
ena.duty(CAR_SPEED)
enb.duty(CAR_SPEED)

def drive_forward():
    in1.value(0); in2.value(1)
    in3.value(0); in4.value(1)

def drive_backward():
    in1.value(1); in2.value(0)
    in3.value(1); in4.value(0)

def stop_car():
    in1.value(0); in2.value(0)
    in3.value(0); in4.value(0)

# --- HÀM XỬ LÝ KHI NHẬN ĐƯỢC LỆNH TỪ LAPTOP ---
def mqtt_callback(topic, msg):
    command = msg.decode('utf-8')
    print("ESP32 nhận lệnh:", command)
    
    if command == "FORWARD":
        set_servo_angle(ANGLE_STRAIGHT) # Trả lái thẳng
        drive_forward()                 # Bánh sau đẩy tới
        
    elif command == "BACKWARD":
        set_servo_angle(ANGLE_STRAIGHT) # Trả lái thẳng
        drive_backward()                # Bánh sau kéo lùi
        
    elif command == "LEFT":
        set_servo_angle(ANGLE_LEFT)     # Bẻ lái trái
        drive_forward()                 # Bánh sau vẫn đẩy tới để xe di chuyển
        
    elif command == "RIGHT":
        set_servo_angle(ANGLE_RIGHT)    # Bẻ lái phải
        drive_forward()                 # Bánh sau vẫn đẩy tới
        
    elif command == "STOP":
        set_servo_angle(ANGLE_STRAIGHT) # Trả thẳng bánh
        stop_car()                      # Tắt động cơ sau

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

# Reset trạng thái ban đầu khi mới bật điện
set_servo_angle(ANGLE_STRAIGHT)
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
