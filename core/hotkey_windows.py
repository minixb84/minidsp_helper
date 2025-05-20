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

        # Ctrl+Alt+Up -> volume up
        self._handlers.append(keyboard.add_hotkey('ctrl+alt+up', self.volume_up_cb))
        # Ctrl+Alt+Down -> volume down
        self._handlers.append(keyboard.add_hotkey('ctrl+alt+down', self.volume_down_cb))
        # Ctrl+Alt+M -> mute toggle
        self._handlers.append(keyboard.add_hotkey('ctrl+alt+m', self.mute_toggle_cb))

        logger.info("HotkeyListenerWindows started")

    def stop(self):
        logger.info("HotkeyListenerWindows stopping")
        for h in self._handlers:
            keyboard.remove_hotkey(h)
        self._handlers.clear()
        logger.info("HotkeyListenerWindows stopped")
