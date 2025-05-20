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
            self.on_volume_up,
            self.on_volume_down,
            self.on_mute_toggle
        )

        self.poller = Poller(self.device, self.volume_state, poll_interval=0.1)
        self.theme_manager = None

    def on_volume_up(self):
        logger.info("on_volume_up called")
        try:
            self.volume_state.handle_event(Event.KB_VOL, +0.5)
            gain = self.device.read_gain_raw()[0]
            logger.info(f"Gain after Volume Up: {gain}")
            wx.CallAfter(self.osd.popup, gain)
        except Exception as e:
            logger.error(f"Exception in on_volume_up: {e}", exc_info=True)

    def on_volume_down(self):
        logger.info("on_volume_down called")
        try:
            self.volume_state.handle_event(Event.KB_VOL, -0.5)
            gain = self.device.read_gain_raw()[0]
            logger.info(f"Gain after Volume Down: {gain}")
            wx.CallAfter(self.osd.popup, gain)
        except Exception as e:
            logger.error(f"Exception in on_volume_down: {e}", exc_info=True)

    def on_mute_toggle(self):
        logger.info("on_mute_toggle called")
        try:
            self.volume_state.handle_event(Event.KB_MUTE_TOGGLE)
            gain = self.device.read_gain_raw()[0]
            logger.info(f"Gain after Mute Toggle: {gain}")
            wx.CallAfter(self.osd.popup, gain)
        except Exception as e:
            logger.error(f"Exception in on_mute_toggle: {e}", exc_info=True)

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

    controller.theme_manager = ThemeManager(app)
    controller.theme_manager.apply("dark")

    controller.start()

    main_win = MainFrame(controller.osd, controller.hotkey_listener, None, title="miniDSP Gain Helper")
    main_win.controller = controller

    main_win.Show()
    exit_code = app.MainLoop()

    controller.stop()
    return exit_code

if __name__ == "__main__":
    main()
