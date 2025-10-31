from ui import UI
from com import Com
from video import Video
from PySide6 import QtCore, QtGui, QtWidgets
import sys
import logging


def main():
    logging.basicConfig(level=logging.INFO)

    com = Com()
    com.start()

    video = Video()
    video.start()

    app = QtWidgets.QApplication(sys.argv)
    ui = UI()
    ui.resize(1280, 720)
    ui.showNormal()
    # ui.showFullScreen()

    last_hit_cnt = None
    health = 100

    def tick():
        nonlocal last_hit_cnt, health

        # 与com交互
        ui.set_color(com.color)
        ui.set_serial_latency(com.latency_ms)

        if com.color == 'red':
            ui.set_healths(health, 100)
        elif com.color == 'blue':
            ui.set_healths(100, health)
        
        if com.hit_cnt and last_hit_cnt and com.hit_cnt != last_hit_cnt:
            health = health - 1
            ui.trigger_hit()
        last_hit_cnt = com.hit_cnt
        
        com.set_port(ui.get_serial_port())
        com.dbus_packet = ui.get_input_packet()

        # 与video交互
        ui.set_frame(video.frame)
        ui.set_fps(video.fps)
        video.set_source(ui.get_video_url())

        # 与server交互
        ui.set_countdown(180)
        ui.set_server_latency(None)

    timer = QtCore.QTimer()
    timer.timeout.connect(tick)
    timer.start(10)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
