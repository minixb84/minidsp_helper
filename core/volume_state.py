# core/volume_state.py
from enum import Enum, auto
import logging

logger = logging.getLogger("minidsp.volume")

class Event(Enum):
    KB_VOL = auto()
    KB_MUTE_TOGGLE = auto()
    RC_VOL = auto()
    RC_MUTE_TOGGLE = auto()

class VolumeState:
    def __init__(self):
        self.keyboard_muted = False
        self.digital_muted = False
        # 기타 상태 변수 초기화

    def handle_event(self, event: Event, payload=None):
        logger.debug(f"Handle event {event} payload={payload}")
        # 이벤트 처리 로직 구현
