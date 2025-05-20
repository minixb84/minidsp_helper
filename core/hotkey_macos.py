# core/hotkey_macos.py
import logging
from core.hotkey_base import HotkeyListenerBase

logger = logging.getLogger("minidsp.hotkey.macos")

class HotkeyListenerMacOS(HotkeyListenerBase):
    def __init__(self, volume_up_cb, volume_down_cb, mute_toggle_cb):
        super().__init__(volume_up_cb, volume_down_cb, mute_toggle_cb)
        # pyobjc, Quartz 이벤트 탭 등 필요한 초기화

    def start(self):
        logger.info("HotkeyListenerMacOS start called")
        # TODO: Quartz 이벤트 탭을 이용해 단축키 후킹 구현
        # 예) CGEventTapCreate 및 RunLoop 추가
        pass

    def stop(self):
        logger.info("HotkeyListenerMacOS stop called")
        # TODO: 이벤트 탭 해제 및 자원 정리
        pass
