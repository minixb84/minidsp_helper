import threading
import time
import logging

logger = logging.getLogger("minidsp.poller")

class Poller:
    def __init__(self, device, volume_state, poll_interval=0.1):
        self.device = device
        self.volume_state = volume_state
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread = None

        self._prev_db = None
        self._prev_dig = None

    def _poll_loop(self):
        logger.info("Poll loop started")
        while not self._stop_event.is_set():
            try:
                db, dig, raw = self.device.read_gain_raw()
                if db == 0.0:
                    time.sleep(self.poll_interval)
                    continue

                if self._prev_db != db or self._prev_dig != dig:
                    logger.debug(f"Volume changed: {self._prev_db} -> {db}, mute: {self._prev_dig} -> {dig}")

                    # 상태 갱신 예: volume_state에 이벤트 전달 가능

                    self._prev_db = db
                    self._prev_dig = dig

                time.sleep(self.poll_interval)
            except Exception:
                logger.exception("Exception in poll loop")
                time.sleep(self.poll_interval)

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
