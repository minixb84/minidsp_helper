# core/poller.py
import threading
import time
import logging

logger = logging.getLogger("minidsp.poller")

class Poller:
    def __init__(self, poll_interval, poll_function):
        self.poll_interval = poll_interval
        self.poll_function = poll_function
        self._stop_event = threading.Event()
        self._thread = None

    def _poll_loop(self):
        logger.info("Poll loop started")
        while not self._stop_event.is_set():
            try:
                self.poll_function()
            except Exception:
                logger.exception("Exception in poll function")
            time.sleep(self.poll_interval)

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
