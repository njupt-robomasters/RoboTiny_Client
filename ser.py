import serial

import threading
import time
import logging

SEND_FREQ = 100


class Ser(threading.Thread):
    RED = 255 << 16
    BLUE = 255

    def __init__(self, level=logging.WARNING):
        super().__init__(daemon=True)

        self.logger = logging.getLogger("Ser")
        self.logger.setLevel(level)

        # 读取
        self.is_connected: bool = False
        self.color: str = None
        self.hit_cnt: int = None
        self.tx_rssi: int = None
        self.rx_rssi: int = None
        self.last_air_ms: int = None

        # 写入
        self.dbus_packet = bytes(10)

        self._port = None
        self._serial = None
        self._last_send_time = 0

    def set_port(self, port: str):
        if self._port == port:
            return

        self.logger.info(f"串口变更: {self._port} -> {port}")
        self._port = port

        self._reset()

    def run(self):
        self.logger.info("串口通信线程启动")

        while True:
            if self._port is None:
                time.sleep(0.1)
                continue

            if self._serial is None:
                self.logger.info(f"尝试打开串口: {self._port}")
                try:
                    self._serial = serial.Serial(self._port)
                except Exception as e:
                    self.logger.info(f"打开串口失败: {e}")
                    time.sleep(0.1)
                    continue
                self.logger.info(f"串口打开成功")

            self._serial_read()
            self._serial_write()

    def _serial_read(self):
        if not self._serial.is_open:
            self.logger.error("串口未打开")
            self._reset()
            return

        try:
            line = self._serial.readline()
        except Exception as e:
            self.logger.error(f"串口读取报错: {e}")
            self._reset()
            return

        if not line:
            self.logger.warning("串口读到空数据")
            return

        try:
            line = line.decode().strip()
        except ValueError as e:
            self.logger.warning(f"串口数据解码错误: {e}")
            return

        self.logger.debug(f"串口读到数据: {line}")

        try:
            parts = line.split(",")
            if len(parts) == 5:
                self.is_connected = True

                color = int(parts[0])
                if color == self.RED:
                    self.color = "red"
                elif color == self.BLUE:
                    self.color = "blue"
                else:
                    self.color = None

                self.hit_cnt = int(parts[1])
                self.tx_rssi = self._filter(self.tx_rssi, int(parts[2]))
                self.rx_rssi = self._filter(self.rx_rssi, int(parts[3]))
                self.last_air_ms = int(parts[4])
                self.logger.debug(f"{self.color=:} {self.hit_cnt=:} {self.tx_rssi=:} {self.rx_rssi=:} {self.last_air_ms=:}")

                if self.last_air_ms > 100:  # 延迟大于100ms的 considered as timeout
                    self.color = None
                    self.hit_cnt = None
                    self.tx_rssi = None
                    self.rx_rssi = None
                    self.last_air_ms = None
            else:
                self.logger.warning(f"串口数据格式错误，期望5个字段，实际收到{len(parts)}个")
        except Exception as e:
            self.logger.warning(f"串口数据解析报错: {e}")

    def _serial_write(self):
        if time.time() - self._last_send_time < 1 / SEND_FREQ:
            return

        try:
            bytes_written = self._serial.write(self.dbus_packet)
            self.logger.debug(f"串口发送数据: {self.dbus_packet.hex()}, 字节数: {bytes_written}")
        except Exception as e:
            self.logger.error(f"串口发送报错: {e}")
            self._reset()

        self._last_send_time = time.time()

    def _reset(self):
        if self._serial:
            self._serial.close()
            self._serial = None

        self.color = None
        self.hit_cnt = None
        self.tx_rssi = None
        self.rx_rssi = None
        self.last_air_ms = None
        self.is_connected = False

    def _filter(self, old, new):
        if new is None:
            return None
        if old is None:
            return new
        return old * 0.9 + new * 0.1


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    ser = Ser(logging.INFO)
    ser.start()
    ser.set_port("COM60")

    while True:
        time.sleep(1)
