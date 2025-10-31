import threading
import cv2
import time
import logging
from collections import deque


class Video(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)

        self.frame = None
        self.fps = 0.0  # 存储视频真实帧率

        self._source = None
        self._cap = None
        self._frame_timestamps = deque()  # 用于统计实时帧率
        self._logger = logging.getLogger('Video')

    def set_source(self, source):
        if source == self._source:
            return

        self._logger.info(f"视频源变更: {self._source} -> {source}")
        self._source = source
        self.fps = 0.0  # 重置帧率
        self._frame_timestamps.clear()  # 清空时间戳队列

        if self._cap:
            self._cap.release()
            self._cap = None
            self.frame = None

    def run(self):
        self._logger.info("视频线程启动")

        while True:
            if self._source is None:
                self._logger.warning("未设置视频源")
                time.sleep(0.1)
                continue

            if not self._cap:
                self._logger.info(f"尝试连接视频源: {self._source}")
                try:
                    self._cap = cv2.VideoCapture(self._source)
                    self._logger.info(f"视频源 {self._source} 连接成功")
                except Exception as e:
                    self._logger.error(f"连接视频源 {self._source} 报错: {e}")
                    time.sleep(0.1)
                    continue

            self._read()

    def _read(self):
        if not self._cap.isOpened():
            self._logger.error("视频流未打开")
            self._cap.release()
            self._cap = None
            self.frame = None
            self.fps = 0.0
            self._frame_timestamps.clear()
            return

        try:
            ret, self.frame = self._cap.read()
        except Exception as e:
            self._logger.error(f"读取帧报错: {e}")
            self._cap.release()
            self._cap = None
            self.frame = None
            self.fps = 0.0
            self._frame_timestamps.clear()
            return

        if not ret:
            self._logger.warning("读取帧失败")
            self._cap.release()
            self._cap = None
            self.frame = None
            self.fps = 0.0
            self._frame_timestamps.clear()
            return

        self.frame = cv2.rotate(self.frame, cv2.ROTATE_90_CLOCKWISE)

        self._update_fps()

    def _update_fps(self):
        """更新帧时间戳"""
        current_time = time.time()
        self._frame_timestamps.append(current_time)

        # 清理超过1秒的时间戳
        while self._frame_timestamps and current_time - self._frame_timestamps[0] > 1.0:
            self._frame_timestamps.popleft()

        self.fps = len(self._frame_timestamps)
        self._logger.debug(f"视频流帧率 {self.fps} FPS")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    video = Video()
    video.start()
    source = "rtsp://192.168.1.1:7070/webcam"  # 请替换为实际的视频源
    video.set_source(source)

    while True:
        if video.frame is not None:
            cv2.imshow(source, video.frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()
