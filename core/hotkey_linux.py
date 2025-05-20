# core/hotkey_linux.py
import logging
from core.hotkey_base import HotkeyListenerBase

logger = logging.getLogger("minidsp.hotkey.linux")

class HotkeyListenerLinux(HotkeyListenerBase):
    def __init__(self, volume_up_cb, volume_down_cb, mute_toggle_cb):
        super().__init__(volume_up_cb, volume_down_cb, mute_toggle_cb)
        # evdev, python-xlib 등 초기화 필요

    def start(self):
        logger.info("HotkeyListenerLinux start called")
        # TODO: evdev 또는 Xlib 키보드 후킹 구현
        pass

    def stop(self):
        logger.info("HotkeyListenerLinux stop called")
        # TODO: 후킹 해제 및 자원 정리
        pass
