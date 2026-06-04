import network
import espnow
import select
import sys
import time

# Chay file nay tren ESP32 phat lenh.
# Ket noi ESP32 nay voi Thonny/Serial, go lenh roi Enter:
# FORWARD, BACKWARD, LEFT, RIGHT, BACK_LEFT, BACK_RIGHT, STOP
# Neu AUTO_APPEND_SLOW = True thi lenh khac STOP se tu dong them _SLOW.

ESPNOW_CHANNEL = 1

# Doi thanh MAC cua ESP32 tren xe.
# Chay main3.py tren xe truoc, doc dong "Receiver MAC: b'...'"
# Roi copy byte MAC do vao day.
RECEIVER_MAC = b"<\x8a\x1f\xa2\xc6\x1c"

COMMANDS = {
    "FORWARD",
    "BACKWARD",
    "LEFT",
    "RIGHT",
    "BACK_LEFT",
    "BACK_RIGHT",
    "STOP",
}

AUTO_APPEND_SLOW = False


def setup_espnow():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.disconnect()

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="espnow-serial-tx", channel=ESPNOW_CHANNEL)

    radio = espnow.ESPNow()
    radio.active(True)
    radio.add_peer(RECEIVER_MAC)

    print("Sender MAC:", sta.config("mac"))
    print("ESP-NOW sender ready, channel:", ESPNOW_CHANNEL)
    print("Nhap lenh serial roi Enter.")
    return radio


def normalize_command(line):
    command = line.strip().upper()
    if not command:
        return None

    if command.endswith("_SLOW"):
        base_command = command[:-5]
    else:
        base_command = command

    if base_command not in COMMANDS:
        print("Lenh khong hop le:", command)
        return None

    if base_command == "STOP":
        return "STOP"

    if AUTO_APPEND_SLOW and not command.endswith("_SLOW"):
        return base_command + "_SLOW"

    return command


radio = setup_espnow()
poller = select.poll()
poller.register(sys.stdin, select.POLLIN)

while True:
    if poller.poll(100):
        line = sys.stdin.readline()
        command = normalize_command(line)
        if command:
            ok = radio.send(RECEIVER_MAC, command.encode("utf-8"))
            print("Da gui:", command, "ok=", ok)

    time.sleep(0.01)
