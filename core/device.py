# core/device.py
import hid
import threading
import logging

logger = logging.getLogger("minidsp.device")

VIDS = {0x2752, 0x04D8}
PIDS = {0x0011, 0x0044, 0x003F}

class MiniDSPDevice:
    def __init__(self, path=None):
        self._lock = threading.Lock()
        self.device = None
        self.path = path
        if path:
            self.open_device(path)
        else:
            self.open_first_device()

    def open_first_device(self):
        devices = self.list_devices()
        if devices:
            self.open_device(devices[0]['path'])
        else:
            raise RuntimeError("No miniDSP device found")

    def open_device(self, path):
        if self.device:
            self.device.close()
        self.device = hid.Device(path=path)
        self.path = path
        logger.info(f"Opened device at {path}")

    @staticmethod
    def list_devices():
        return [
            d for d in hid.enumerate()
            if d['vendor_id'] in VIDS and d['product_id'] in PIDS
        ]

    def write(self, data: bytes):
        with self._lock:
            return self.device.write(data)

    def read(self, size=65, timeout=50):
        with self._lock:
            return self.device.read(size, timeout)

    def close(self):
        if self.device:
            self.device.close()
