from PySide6 import QtCore, QtGui
import time
import logging

from ser import Ser
from video import Video
from mqtt import MQTT
from ui import UI

FULL_SCREEN = True

ser = Ser()
video = Video()
mqtt = MQTT()
ui = UI()

hp = 100
last_hit_cnt = None


def update_com():
    global hp, last_hit_cnt

    # 设置颜色
    ui.set_color(ser.color)

    # 设置串口状态
    ui.set_serial_status(ser.is_connected, ser.tx_rssi, ser.rx_rssi)

    # 击打检测
    hit_cnt = ser.hit_cnt
    if hit_cnt != None:  # 串口连上了
        if hit_cnt != last_hit_cnt:  # 跳变
            if last_hit_cnt != None:  # 不是连上的第一次跳变
                hp -= 1
                ui.trigger_hit()
    last_hit_cnt = ser.hit_cnt

    # 设置血量
    if ser.color == 'red':
        ui.set_red_hp(hp)
    elif ser.color == 'blue':
        ui.set_blue_hp(hp)

    # 设置串口
    ser.set_port(ui.get_serial_port())

    # 设置键鼠报文
    ser.dbus_packet = ui.get_dbus_packet()


def update_video():
    ui.set_frame(video.frame)
    ui.set_video_fps(video.fps)
    video.set_source(ui.get_video_source())


last_yellow_card_ms = None
yellow_card_local = None
last_reset_hp_ms = None
last_color = None


def update_mqtt():
    global hp, last_yellow_card_ms, last_reset_hp_ms, last_color, yellow_card_local

    # MQTT频率
    ui.set_mqtt_freq(mqtt.freq)

    # 顶部比赛信息
    ui.set_countdown(mqtt.referee_msg["countdown"])
    ui.set_red_name(mqtt.referee_msg["red"]["name"])
    ui.set_blue_name(mqtt.referee_msg["blue"]["name"])
    ui.set_red_hp(mqtt.referee_msg["red"]["hp"])
    ui.set_blue_hp(mqtt.referee_msg["blue"]["hp"])

    # 颜色变化时，防止意外的黄牌警告和重置血量
    if last_color != ser.color:
        last_yellow_card_ms = None
        last_reset_hp_ms = None
    last_color = ser.color

    # 黄牌警告
    if ser.color:  # 串口连上了，能获取到颜色
        yellow_card_ms = mqtt.referee_msg[ser.color]["yellow_card_ms"]
        if yellow_card_ms is not None:  # MQTT连上了
            if yellow_card_ms != last_yellow_card_ms:  # 跳变
                if last_yellow_card_ms is not None:  # 不是连上的第一次跳变
                    hp -= 10  # 扣血10%
                    yellow_card_local = time.time()
        last_yellow_card_ms = yellow_card_ms

    # 中心文字
    state = mqtt.referee_msg["state"]
    txt = mqtt.referee_msg["txt"]
    countdown = mqtt.referee_msg["countdown"]
    RED = QtGui.QColor(255, 84, 84)
    BLUE = QtGui.QColor(88, 140, 255)
    if state == 1:  # 红方胜
        if ser.color == "red":
            ui.set_center_txt("胜利", txt, RED)
        elif ser.color == "blue":
            ui.set_center_txt("失败", txt)
    elif state == 2:  # 蓝方胜
        if ser.color == "red":
            ui.set_center_txt("失败", txt)
        elif ser.color == "blue":
            ui.set_center_txt("胜利", txt, BLUE)
    elif state == 3:  # 平局
        ui.set_center_txt("平局", txt)
    elif yellow_card_local is not None:  # 黄牌警告未结束
        remaining = int(round(yellow_card_local + 5 - time.time()))
        if remaining <= 0:
            yellow_card_local = None
        ui.set_center_txt("黄牌", f"扣血10点，{remaining}秒后消失", "yellow")
    elif countdown and countdown >= -5 and countdown <= 0:
        ui.set_center_txt(str(-countdown), "比赛即将开始")
    else:
        ui.set_center_txt("", "")

    # 重置血量
    if ser.color:  # 串口连上了，能获取到颜色
        reset_hp_ms = mqtt.referee_msg[ser.color]["reset_hp_ms"]
        if reset_hp_ms is not None:  # MQTT连上了
            if reset_hp_ms != last_reset_hp_ms:  # 跳变
                if last_reset_hp_ms is not None:  # 不是连上的第一次跳变
                    hp = 100
        last_reset_hp_ms = reset_hp_ms

    # 发送MQTT消息
    mqtt.set_broker_url(ui.get_mqtt_url())
    mqtt.color = ser.color
    mqtt.client_msg = {"hp": hp,
                       "com_is_connected": ser.is_connected,
                       "video_fps": video.fps,
                       "tx_rssi": ser.tx_rssi,
                       "rx_rssi": ser.rx_rssi
                       }


def update():
    update_com()
    update_video()
    update_mqtt()


def main():
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')

    ser.start()
    video.start()
    mqtt.start()

    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(10)

    if FULL_SCREEN:
        ui.loop()
    else:
        ui.loop((1280, 720))


if __name__ == "__main__":
    main()
