# app.py
import wx
from core.device import MiniDSPDevice
from core.volume_state import VolumeState
from core.hotkey import HotkeyListener
from core.poller import Poller
from gui.main_wx import MainFrame
from gui.volume_osd_wx import VolumeOSD
import logging

def main():
    logging.basicConfig(level=logging.INFO)
    app = wx.App(False)
    
    device = MiniDSPDevice()
    volume_state = VolumeState()
    osd = VolumeOSD()
    
    def on_volume_up():
        logging.info("Volume Up")
        # volume_state.handle_event(...)
    
    def on_volume_down():
        logging.info("Volume Down")
        # volume_state.handle_event(...)
    
    def on_mute_toggle():
        logging.info("Mute Toggle")
        # volume_state.handle_event(...)
    
    hotkey_listener = HotkeyListener(on_volume_up, on_volume_down, on_mute_toggle)
    hotkey_listener.start()
    
    poller = Poller(0.1, lambda: None)  # 실제 poll 함수 연결 필요
    poller.start()
    
    main_win = MainFrame(osd)
    main_win.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()
