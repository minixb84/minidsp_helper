import hid
import threading
import time
import logging

logger = logging.getLogger("minidsp.device")

VIDS = {0x2752, 0x04D8}
PIDS = {0x0011, 0x0044, 0x003F}

PAD = lambda p: b"\x00" + p.ljust(64, b"\xFF")
CHK = lambda *b: sum(b) & 0xFF

class MiniDSPDevice:
    def __init__(self, path=None):
        self._lock = threading.Lock()
        self.device = None
        self.path = None
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

    def write(self, data: bytes, retries=5, delay=0.02):
        with self._lock:
            for _ in range(retries):
                try:
                    return self.device.write(data)
                except hid.HIDException as e:
                    if "0x000003E5" in str(e):
                        time.sleep(delay)
                        continue
                    raise
            return self.device.write(data)

    def read(self, size=65, timeout=50):
        with self._lock:
            return self.device.read(size, timeout)

    def close(self):
        if self.device:
            self.device.close()
            self.device = None

    def read_gain_raw(self):
        with self._lock:
            req = bytes([0x05,0x05,0xFF,0xDA,0x02, CHK(0x05,0x05,0xFF,0xDA,0x02)])
            self.device.write(PAD(req))
            t0 = time.time()
            while time.time() - t0 < 0.3:
                r = self.device.read(65, 50)
                if not r:
                    continue
                if r[0] == 0:
                    r = r[1:]
                if bytes(r[:4]) == b"\x06\x05\xFF\xDA":
                    val = r[4]
                    db = -0.5 * val
                    muted = bool(r[5])
                    return db, muted, bytes(r)
            raise RuntimeError("GAIN read timeout")

    def write_gain(self, db: float):
        with self._lock:
            self.device.read(65, 5)  # flush
            db = max(min(db, 0.0), -127.0)
            val = int(round(-2 * db))
            cmd = bytes([0x03, 0x42, val, CHK(0x03, 0x42, val)])
            self.write(PAD(cmd))

    def write_mute(self, toggle: bool):
        with self._lock:
            b = 0x01 if toggle else 0x00
            cmd = bytes([0x03, 0x17, b, CHK(0x03, 0x17, b)])
            self.write(PAD(cmd))
