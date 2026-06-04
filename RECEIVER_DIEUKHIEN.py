import network
import espnow
import time
from machine import Pin, PWM

# Chay file nay tren ESP32 gan tren xe.
# Board se nhan lenh ESP-NOW va dieu khien servo + L298N.

ESPNOW_CHANNEL = 1

# --- SERVO MG90S ---
servo = PWM(Pin(19), freq=50)

ANGLE_STRAIGHT = 90
ANGLE_LEFT = 120
ANGLE_RIGHT = 60
SERVO_STEP_DELAY = 0.02
SERVO_SETTLE_MS = 150
current_angle = ANGLE_STRAIGHT


def servo_duty_from_angle(angle):
    min_duty = 40
    max_duty = 115
    return int(min_duty + (angle / 180) * (max_duty - min_duty))


def smooth_servo(target_angle):
    global current_angle
    target_angle = max(0, min(180, target_angle))
    if current_angle == target_angle:
        servo.duty(servo_duty_from_angle(target_angle))
        time.sleep_ms(SERVO_SETTLE_MS)
        return

    step = 1 if target_angle > current_angle else -1
    for angle in range(current_angle, target_angle + step, step):
        servo.duty(servo_duty_from_angle(angle))
        time.sleep(SERVO_STEP_DELAY)

    current_angle = target_angle
    servo.duty(servo_duty_from_angle(target_angle))
    time.sleep_ms(SERVO_SETTLE_MS)


# --- L298N ---
ena = PWM(Pin(32), freq=1000)
in1 = Pin(26, Pin.OUT)
in2 = Pin(27, Pin.OUT)
in3 = Pin(14, Pin.OUT)
in4 = Pin(12, Pin.OUT)
enb = PWM(Pin(13), freq=1000)

CAR_SPEED_NORMAL = 450
CAR_SPEED_SLOW = CAR_SPEED_NORMAL - 50
MOTOR_B_REVERSED = True


def set_speed(speed):
    speed = max(0, min(1023, speed))
    ena.duty(speed)
    enb.duty(speed)


def drive_forward():
    in1.value(0)
    in2.value(1)
    if MOTOR_B_REVERSED:
        in3.value(1)
        in4.value(0)
    else:
        in3.value(0)
        in4.value(1)


def drive_backward():
    in1.value(1)
    in2.value(0)
    if MOTOR_B_REVERSED:
        in3.value(0)
        in4.value(1)
    else:
        in3.value(1)
        in4.value(0)


def stop_car():
    in1.value(0)
    in2.value(0)
    in3.value(0)
    in4.value(0)


set_speed(CAR_SPEED_NORMAL)
stop_car()

# --- HC-SR04 ---
TRIG_PIN = 23
ECHO_PIN = 22
OBSTACLE_CM = 5
REVERSE_MS = 1000
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
    stop_car()
    smooth_servo(ANGLE_STRAIGHT)
    set_speed(CAR_SPEED_SLOW)
    drive_backward()
    time.sleep(REVERSE_MS / 1000)
    stop_car()


def handle_command(command_raw):
    command_raw = command_raw.strip().upper()
    print("ESP-NOW nhan lenh:", command_raw)

    is_slow = False
    command = command_raw
    if command_raw.endswith("_SLOW"):
        is_slow = True
        command = command_raw[:-5]

    stop_car()
    set_speed(CAR_SPEED_SLOW if is_slow else CAR_SPEED_NORMAL)

    if command == "FORWARD":
        smooth_servo(ANGLE_STRAIGHT)
        drive_forward()
    elif command == "BACKWARD":
        smooth_servo(ANGLE_STRAIGHT)
        drive_backward()
    elif command == "LEFT":
        smooth_servo(ANGLE_LEFT)
        drive_forward()
    elif command == "RIGHT":
        smooth_servo(ANGLE_RIGHT)
        drive_forward()
    elif command == "BACK_LEFT":
        smooth_servo(ANGLE_LEFT)
        drive_backward()
    elif command == "BACK_RIGHT":
        smooth_servo(ANGLE_RIGHT)
        drive_backward()
    elif command == "STOP":
        smooth_servo(ANGLE_STRAIGHT)


def setup_espnow():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.disconnect()

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="espnow-car-rx", channel=ESPNOW_CHANNEL)

    radio = espnow.ESPNow()
    radio.active(True)
    print("Receiver MAC:", sta.config("mac"))
    print("ESP-NOW receiver ready, channel:", ESPNOW_CHANNEL)
    return radio


radio = setup_espnow()
smooth_servo(ANGLE_STRAIGHT)
stop_car()

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

    host, msg = radio.recv(0)
    if msg:
        try:
            handle_command(msg.decode("utf-8"))
        except Exception as e:
            print("Lenh khong hop le:", msg, e)

    time.sleep(0.01)
