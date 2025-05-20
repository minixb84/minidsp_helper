# core/hotkey_windows.py
import logging
from core.hotkey_base import HotkeyListenerBase
import keyboard  # keyboard 라이브러리 필요 (pip install keyboard)

logger = logging.getLogger("minidsp.hotkey.windows")

class HotkeyListenerWindows(HotkeyListenerBase):
    def __init__(self, volume_up_cb, volume_down_cb, mute_toggle_cb):
        super().__init__(volume_up_cb, volume_down_cb, mute_toggle_cb)
        self._handlers = []

    def start(self):
        logger.info("HotkeyListenerWindows starting")

        def vol_up():
            logger.info("Volume Up callback triggered")
            self.volume_up_cb()

        def vol_down():
            logger.info("Volume Down callback triggered")
            self.volume_down_cb()

        def mute_toggle():
            logger.info("Mute Toggle callback triggered")
            self.mute_toggle_cb()

        self._handlers.append(
            keyboard.add_hotkey('ctrl+alt+up', vol_up, suppress=True)
        )
        self._handlers.append(
            keyboard.add_hotkey('ctrl+alt+down', vol_down, suppress=True)
        )
        self._handlers.append(
            keyboard.add_hotkey('ctrl+alt+m', mute_toggle, suppress=True)
        )

        logger.info("HotkeyListenerWindows started")

    def stop(self):
        logger.info("HotkeyListenerWindows stopping")
        for h in self._handlers:
            keyboard.remove_hotkey(h)
        self._handlers.clear()
        logger.info("HotkeyListenerWindows stopped")
