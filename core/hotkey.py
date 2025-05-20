# core/hotkey.py
from pynput import keyboard, mouse
import logging
from threading import Thread

logger = logging.getLogger("minidsp.hotkey")

class HotkeyListener:
    def __init__(self, volume_up_callback, volume_down_callback, mute_toggle_callback):
        self.volume_up = volume_up_callback
        self.volume_down = volume_down_callback
        self.mute_toggle = mute_toggle_callback
        self._keyboard_listener = None
        self._mouse_listener = None

    def _on_key_press(self, key):
        try:
            if key == keyboard.Key.media_volume_up:
                self.volume_up()
            elif key == keyboard.Key.media_volume_down:
                self.volume_down()
            elif key == keyboard.Key.media_volume_mute:
                self.mute_toggle()
            # 추가 단축키 조합 예: alt+F11 등
        except Exception:
            logger.exception("Exception in key press handler")

    def _on_scroll(self, x, y, dx, dy):
        if dy > 0:
            self.volume_up()
        elif dy < 0:
            self.volume_down()

    def start(self):
        self._keyboard_listener = keyboard.Listener(on_press=self._on_key_press)
        self._mouse_listener = mouse.Listener(on_scroll=self._on_scroll)
        self._keyboard_listener.start()
        self._mouse_listener.start()

    def stop(self):
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()
