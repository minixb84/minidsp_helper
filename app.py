# app.py
import wx
import logging
from core.device import MiniDSPDevice
from core.volume_state import VolumeState, Event
from core.hotkey import HotkeyListener
from core.poller import Poller
from gui.main_wx import MainFrame
from gui.volume_osd_wx import VolumeOSD
from gui.theme_manager_wx import ThemeManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("minidsp.app")

class AppController:
    def __init__(self):
        self.device = MiniDSPDevice()
        self.volume_state = VolumeState(self.device)
        self.osd = VolumeOSD()

        self.hotkey_listener = HotkeyListener(
            volume_up_callback=self.on_volume_up,
            volume_down_callback=self.on_volume_down,
            mute_toggle_callback=self.on_mute_toggle
        )

        self.poller = Poller(self.device, self.volume_state, poll_interval=0.1)
        self.theme_manager = None  # wx.App 생성 후 초기화 필요

    def on_volume_up(self):
        logger.info("Volume Up triggered")
        try:
            self.volume_state.handle_event(Event.KB_VOL, +0.5)
            gain = self.device.read_gain_raw()[0]
            logger.info(f"Gain after Volume Up: {gain}")
            self.osd.popup(gain)
        except Exception as e:
            logger.error(f"Exception in on_volume_up: {e}", exc_info=True)

    def on_volume_down(self):
        logger.info("Volume Down triggered")
        self.volume_state.handle_event(Event.KB_VOL, -0.5)
        gain = self.device.read_gain_raw()[0]
        self.osd.popup(gain)

    def on_mute_toggle(self):
        logger.info("Mute Toggle triggered")
        self.volume_state.handle_event(Event.KB_MUTE_TOGGLE)
        gain = self.device.read_gain_raw()[0]
        self.osd.popup(gain)

    def start(self):
        self.hotkey_listener.start()
        self.poller.start()

    def stop(self):
        self.poller.stop()
        self.hotkey_listener.stop()
        self.device.close()

    def change_device(self, path):
        logger.info(f"Changing device to {path}")
        self.poller.stop()
        self.device.open_device(path)
        self.poller.start()

def main():
    app = wx.App(False)

    controller = AppController()

    # 테마 매니저 초기화 및 다크 모드 적용
    controller.theme_manager = ThemeManager(app)
    controller.theme_manager.apply("dark")

    controller.start()

    main_win = MainFrame(controller.osd, controller.hotkey_listener, None, title="miniDSP Gain Helper")

    # MainFrame에 controller 객체 연결
    main_win.controller = controller

    main_win.Show()
    exit_code = app.MainLoop()

    controller.stop()
    return exit_code

if __name__ == "__main__":
    main()
