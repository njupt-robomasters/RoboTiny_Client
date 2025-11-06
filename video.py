import threading
import av
import cv2
import time
from collections import deque
import logging


class Video(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)

        self.source = None
        self.container = None
        self.logger = logging.getLogger('Video')

        # 状态变量
        self.frame = None
        self.fps = None  # 存储视频真实帧率
        self.frame_timestamps = deque()  # 用于统计实时帧率

    def set_source(self, source):
        if source == self.source:
            return

        self.logger.info(f"视频源变更: {self.source} -> {source}")
        self.source = source

        self._reset_data()

        if self.container:
            self.container.close()
            self.container = None

    def run(self):
        self.logger.info("视频线程启动")

        while True:
            if self.source is None:
                self.logger.warning("未设置视频源")
                time.sleep(0.1)
                continue

            if self.container is None:
                self.logger.info(f"尝试连接视频源: {self.source}")
                try:
                    self.container = av.open(self.source, options={"timeout": "3000000"})  # 超时3秒（单位：微秒）
                    self.logger.info(f"视频源 {self.source} 连接成功")
                except Exception as e:
                    self.logger.error(f"连接视频源 {self.source} 报错: {e}")
                    time.sleep(0.1)
                    continue

            self._read()

    def _read(self):
        try:
            av_frame = next(self.container.decode(video=0))
            # PyAV 返回的帧是 AVFrame 对象，需要转换为 numpy 数组给 OpenCV 使用（BGR格式）
            frame = av_frame.to_ndarray(format='bgr24')
            self.frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            self._update_fps()
        except av.FFmpegError as e:
            self.logger.error("视频流连接超时")
            self.container.close()
            self.container = None
            self._reset_data()
            return

    def _update_fps(self):
        """更新帧时间戳"""
        current_time = time.time()
        self.frame_timestamps.append(current_time)

        # 清理超过1秒的时间戳
        while self.frame_timestamps and current_time - self.frame_timestamps[0] > 1.0:
            self.frame_timestamps.popleft()

        self.fps = len(self.frame_timestamps)
        self.logger.debug(f"视频流帧率 {self.fps} FPS")

    def _reset_data(self):
        self.frame = None
        self.fps = None
        self.frame_timestamps.clear()


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
