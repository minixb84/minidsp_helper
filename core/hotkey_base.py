# core/hotkey_base.py
from abc import ABC, abstractmethod

class HotkeyListenerBase(ABC):
    def __init__(self, volume_up_cb, volume_down_cb, mute_toggle_cb):
        self.volume_up_cb = volume_up_cb
        self.volume_down_cb = volume_down_cb
        self.mute_toggle_cb = mute_toggle_cb

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass
