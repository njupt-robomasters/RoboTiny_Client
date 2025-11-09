from PySide6 import QtCore
import logging

from ser import Ser
from video import Video
from mqtt import MQTT
from ui import UI

ser = Ser()
video = Video()
mqtt = MQTT()
ui = UI()

hp = 100
last_hit_cnt = None
last_yellow_card_ms = None
last_reset_hp_ms = None
last_color = None


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


def update_mqtt():
    global hp, last_yellow_card_ms, last_reset_hp_ms, last_color

    # MQTT频率
    ui.set_mqtt_freq(mqtt.freq)

    # 顶部比赛信息
    ui.set_countdown(mqtt.referee_msg["countdown"])
    ui.set_red_hp(mqtt.referee_msg["red"]["hp"])
    ui.set_blue_hp(mqtt.referee_msg["blue"]["hp"])

    # 颜色跳变，防止重复黄牌警告和重置血量
    if last_color != ser.color:
        last_yellow_card_ms = None
        last_reset_hp_ms = None
    last_color = ser.color

    # 黄牌警告

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

    ui.loop((1280, 720))


if __name__ == "__main__":
    main()
