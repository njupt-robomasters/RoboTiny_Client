import threading
import serial
import time
import logging


class Com(threading.Thread):
    RED = 255 << 16
    BLUE = 255

    def __init__(self):
        super().__init__(daemon=True)

        self.port = None
        self.serial = None
        self.last_send_time = 0
        self.logger = logging.getLogger('Com')

        # 串口接收
        self.color = None
        self.hit_cnt = None
        self.tx_rssi = None
        self.rx_rssi = None
        self.last_receive_ms = None
        self.is_connected = False

        # 串口发送
        self.dbus_packet = bytes(10)

    def set_port(self, port: str):
        if self.port == port:
            return

        self.logger.info(f"串口变更: {self.port} -> {port}")
        self.port = port

        if self.serial:
            self._reset_data()
            self.serial.close()
            self.serial = None

    def run(self):
        self.logger.info("串口通信线程启动")

        while True:
            if not self.port:
                self.logger.warning("未设置串口端口")
                time.sleep(0.1)
                continue

            if not self.serial:
                self.logger.info(f"尝试打开串口: {self.port}")
                try:
                    self.serial = serial.Serial(self.port)
                except Exception as e:
                    self.logger.error(f"打开串口 {self.port} 失败: {e}")
                    time.sleep(0.1)
                    continue
                self.logger.info(f"串口 {self.port} 打开成功")

            self._read()
            self._send()

    def _read(self):
        if not self.serial.is_open:
            self.logger.error("串口未打开")
            self._reset_data()
            self.serial.close()
            self.serial = None
            return

        try:
            line = self.serial.readline()
        except Exception as e:
            self.logger.error(f"串口读取报错: {e}")
            self._reset_data()
            self.serial.close()
            self.serial = None
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

        parts = line.split(',')
        if len(parts) == 5:
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
            self.last_receive_ms = int(parts[4])
            self.is_connected = True

            self.logger.debug(
                f"串口数据解析完毕，颜色：{self.color}, 击打次数：{self.hit_cnt}, 发送RSSI: {self.tx_rssi}, 接收RSSI: {self.rx_rssi}, 最后一次接收时间：{self.last_receive_ms}")
            if self.last_receive_ms > 100:  # 延迟大于100ms的 considered as timeout
                self._reset_data()
                self.is_connected = True
        else:
            self.logger.warning(f"串口数据格式错误，期望3个字段，实际收到{len(parts)}个")

    def _send(self):
        if time.time() - self.last_send_time < 0.01:
            return

        try:
            bytes_written = self.serial.write(self.dbus_packet)
            self.logger.debug(
                f"串口发送数据: {self.dbus_packet.hex()}, 字节数: {bytes_written}")
        except Exception as e:
            self.logger.error(f"串口发送报错: {e}")

        self.last_send_time = time.time()

    def _reset_data(self):
        self.color = None
        self.hit_cnt = None
        self.tx_rssi = None
        self.rx_rssi = None
        self.last_receive_ms = None
        self.is_connected = False

    def _filter(self, old, new):
        if new is None:
            return None
        if old is None:
            return new
        return old * 0.9 + new * 0.1


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    com = Com()
    com.start()
    com.set_port("COM53")

    while True:
        time.sleep(1)
