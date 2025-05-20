import logging
from pynput import keyboard, mouse

logger = logging.getLogger("minidsp.hotkey")

class HotkeyListener:
    def __init__(self, volume_up_callback, volume_down_callback, mute_toggle_callback):
        self.volume_up_cb = volume_up_callback
        self.volume_down_cb = volume_down_callback
        self.mute_toggle_cb = mute_toggle_callback

        self._keyboard_listener = None
        self._mouse_listener = None

        self._media_enabled = True
        self._alt_enabled = True
        self._shift_enabled = True

        self._alt_pressed = False

def _on_key_press(self, key):
    logger.debug(f"Key pressed: {key}")

    def _on_key_press(self, key):
        try:
            if not self._media_enabled and not self._alt_enabled:
                return

            if key == keyboard.Key.media_volume_up and self._media_enabled:
                self.volume_up_cb()
            elif key == keyboard.Key.media_volume_down and self._media_enabled:
                self.volume_down_cb()
            elif key == keyboard.Key.media_volume_mute and self._media_enabled:
                self.mute_toggle_cb()
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self._alt_pressed = True
            elif self._alt_pressed and self._alt_enabled:
                if hasattr(key, "vk"):
                    if key.vk == 0x7A:
                        self.volume_up_cb()
                    elif key.vk == 0x79:
                        self.volume_down_cb()
                    elif key.vk == 0x7B:
                        self.mute_toggle_cb()
        except Exception:
            logger.exception("Exception in _on_key_press")

def _on_key_press(self, key):
    logger.debug(f"Key pressed: {key}")

    def _on_key_release(self, key):
        if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            self._alt_pressed = False

    def _on_scroll(self, x, y, dx, dy):
        try:
            if not self._shift_enabled:
                return
            if dy > 0:
                self.volume_up_cb()
            elif dy < 0:
                self.volume_down_cb()
        except Exception:
            logger.exception("Exception in _on_scroll")

    def start(self):
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._mouse_listener = mouse.Listener(
            on_scroll=self._on_scroll
        )

        self._keyboard_listener.start()
        self._mouse_listener.start()

        logger.info("HotkeyListener started")

    def stop(self):
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

        logger.info("HotkeyListener stopped")

    def enable_media_keys(self, flag: bool):
        self._media_enabled = flag
        logger.info(f"Media keys enabled set to {flag}")

    def enable_alt_keys(self, flag: bool):
        self._alt_enabled = flag
        logger.info(f"Alt keys enabled set to {flag}")

    def enable_shift_keys(self, flag: bool):
        self._shift_enabled = flag
        logger.info(f"Shift keys enabled set to {flag}")

    def pause_hotkeys(self):
        self._media_enabled = False
        self._alt_enabled = False
        self._shift_enabled = False
        logger.info("All hotkeys paused")

    def resume_hotkeys(self):
        self._media_enabled = True
        self._alt_enabled = True
        self._shift_enabled = True
        logger.info("All hotkeys resumed")
