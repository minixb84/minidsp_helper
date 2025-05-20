import logging
from enum import Enum, auto
from threading import Lock

logger = logging.getLogger("minidsp.volume")

class Event(Enum):
    KB_VOL = auto()
    KB_MUTE_TOGGLE = auto()
    RC_VOL = auto()
    RC_MUTE_TOGGLE = auto()

class VolumeState:
    def __init__(self, device):
        self.device = device
        self.lock = Lock()

        self.keyboard_muted = False
        self.digital_muted = False
        self.saved_gain = None
        self._skip_next_rc_vol = False
        self._skip_save_only = False
        self._ignore_poll_count = 0

        self.prev_kb = False
        self.prev_dig = False

    def suspend_polling(self):
        class DummyContext:
            def __enter__(inner_self):
                self._ignore_poll_count += 1
            def __exit__(inner_self, exc_type, exc_val, exc_tb):
                self._ignore_poll_count -= 1
        return DummyContext()

    def current_gain(self):
        with self.lock:
            db, muted, _ = self.device.read_gain_raw()
            return db

    def apply_gain(self, db: float):
        with self.suspend_polling():
            self.device.write_gain(db)
            logger.info(f"Applied gain: {db:.1f} dB")

    def apply_delta(self, delta: float):
        cur = self.current_gain()
        tgt = max(min(cur + delta, 0.0), -127.0)
        self.apply_gain(tgt)

    def apply_digital_unmute(self):
        with self.suspend_polling():
            self.device.write_mute(False)
            logger.info("Digital unmute applied")
        self.digital_muted = False

    def handle_event(self, event: Event, payload=None):
        logger.debug(f"Handling event {event}, payload={payload}")

        if event == Event.KB_VOL:
            if self.keyboard_muted and not self.digital_muted:
                self.apply_gain(self.saved_gain or -20.0)
                self.keyboard_muted = False
            elif not self.keyboard_muted and not self.digital_muted:
                self.apply_delta(payload)
                self.saved_gain = self.current_gain()
            else:
                self.apply_digital_unmute()
                self.apply_gain(self.saved_gain or -20.0)
                self._skip_save_only = True
            return

        if event == Event.KB_MUTE_TOGGLE:
            if self.keyboard_muted and not self.digital_muted:
                self.apply_gain(self.saved_gain or -20.0)
                self.keyboard_muted = False
            elif not self.keyboard_muted and not self.digital_muted:
                self._skip_next_rc_vol = True
                self.saved_gain = self.current_gain()
                self.apply_gain(-127.0)
                self.keyboard_muted = True
            else:
                self.apply_digital_unmute()
                self._skip_save_only = True
            return
