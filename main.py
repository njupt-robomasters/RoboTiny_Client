from PySide6 import QtWidgets, QtCore
import sys
import logging

from com import Com
from video import Video
from ui import UI

qt = QtWidgets.QApplication(sys.argv)
com = Com()
video = Video()
ui = UI()

hp = 100
last_hit_cnt = None


def update_com():
    global hp, last_hit_cnt

    ui.set_color(com.color)
    ui.set_serial_status(com.is_connected, com.tx_rssi, com.rx_rssi)

    # 击打检测
    if com.hit_cnt and last_hit_cnt and com.hit_cnt != last_hit_cnt:
        hp -= 1
        ui.trigger_hit()
    last_hit_cnt = com.hit_cnt

    # 更新血量
    if com.color == 'red':

        ui.set_red_hp(hp)
        ui.set_blue_hp(100)
    elif com.color == 'blue':
        ui.set_blue_hp(hp)
        ui.set_red_hp(100)

    com.set_port(ui.get_serial_port())
    com.dbus_packet = ui.get_dbus_packet()


def update_video():
    ui.set_frame(video.frame)
    ui.set_fps(video.fps)
    video.set_source(ui.get_video_source())


def update_server():
    ui.set_countdown(180)
    ui.set_server_latency(None)


def update():
    update_com()
    update_video()
    update_server()


def main():
    logging.basicConfig(level=logging.INFO)

    com.start()
    video.start()

    # ui.resize(1280, 720)
    # ui.showNormal()
    # ui.showMaximized()
    ui.showFullScreen()
    ui.show_on_current_screen()

    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(10)

    sys.exit(qt.exec())


if __name__ == "__main__":
    main()
