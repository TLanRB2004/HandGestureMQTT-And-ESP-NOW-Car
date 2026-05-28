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
RIGHT_MOTOR_REVERSED = True

CAR_SPEED_NORMAL = 600
CAR_SPEED_SLOW = 350

def set_speed(speed):
    ena.duty(speed)
    enb.duty(speed)

set_speed(CAR_SPEED_NORMAL)

def drive_forward():
    in1.value(0); in2.value(1)
    if RIGHT_MOTOR_REVERSED:
        in3.value(1); in4.value(0)
    else:
        in3.value(0); in4.value(1)

def drive_backward():
    in1.value(1); in2.value(0)
    if RIGHT_MOTOR_REVERSED:
        in3.value(0); in4.value(1)
    else:
        in3.value(1); in4.value(0)

def stop_car():
    in1.value(0); in2.value(0)
    in3.value(0); in4.value(0)

# --- CẢM BIẾN SIÊU ÂM HC-SR04 ---
TRIG_PIN = 19
ECHO_PIN = 21
OBSTACLE_CM = 20
REVERSE_MS = 300
PING_INTERVAL_MS = 60
PING_TIMEOUT_MS = 120

trig = Pin(TRIG_PIN, Pin.OUT)
trig.value(0)
echo = Pin(ECHO_PIN, Pin.IN)

echo_start_us = 0
echo_duration_us = 0
echo_done = False
echo_waiting = False
last_ping_ms = time.ticks_ms()


def _echo_irq(pin):
    global echo_start_us, echo_duration_us, echo_done, echo_waiting
    if pin.value():
        echo_start_us = time.ticks_us()
    else:
        echo_duration_us = time.ticks_diff(time.ticks_us(), echo_start_us)
        echo_done = True
        echo_waiting = False


echo.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=_echo_irq)


def trigger_ping():
    global echo_waiting, echo_done
    echo_done = False
    echo_waiting = True
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)


def obstacle_detected():
    global echo_done
    if not echo_done:
        return False
    echo_done = False
    distance_cm = (echo_duration_us * 0.0343) / 2
    return 0 < distance_cm < OBSTACLE_CM


def avoid_obstacle():
    smooth_servo(ANGLE_STRAIGHT)
    set_speed(CAR_SPEED_SLOW)
    drive_backward()
    time.sleep(REVERSE_MS / 1000)
    stop_car()

# --- HÀM XỬ LÝ LỆNH TỪ AI ---
def mqtt_callback(topic, msg):
    command_raw = msg.decode('utf-8').strip()
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
        now_ms = time.ticks_ms()
        if (not echo_waiting) and time.ticks_diff(now_ms, last_ping_ms) >= PING_INTERVAL_MS:
            trigger_ping()
            last_ping_ms = now_ms

        if echo_waiting and time.ticks_diff(now_ms, last_ping_ms) >= PING_TIMEOUT_MS:
            echo_waiting = False

        if obstacle_detected():
            print("Phat hien vat can -> lui xe")
            avoid_obstacle()

        client.check_msg()
        time.sleep(0.01)
except KeyboardInterrupt:
    print("Ngắt kết nối!")
    stop_car()
    client.disconnect()
