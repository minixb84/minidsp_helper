# gui/main_wx.py
import wx
import wx.adv
import logging
from core.device import MiniDSPDevice

logger = logging.getLogger("minidsp.gui")

class MainFrame(wx.Frame):
    def __init__(self, volume_osd, hotkey_controller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.volume_osd = volume_osd
        self.hotkey_controller = hotkey_controller
        self.controller = None  # AppController 객체 연결용

        self.SetTitle("miniDSP Gain Helper")
        self.SetSize((300, 400))
        self.Center()

        self.create_menu()
        self.create_controls()
        self.create_tray_icon()

        self.Bind(wx.EVT_CLOSE, self.on_close)

    def create_menu(self):
        menubar = wx.MenuBar()

        file_menu = wx.Menu()
        pause_item = file_menu.Append(wx.ID_ANY, "Pause Hotkeys")
        resume_item = file_menu.Append(wx.ID_ANY, "Resume Hotkeys")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "Exit")

        menubar.Append(file_menu, "&File")
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.on_pause, pause_item)
        self.Bind(wx.EVT_MENU, self.on_resume, resume_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)

    def create_controls(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.cb_media = wx.CheckBox(panel, label="Enable Media Keys & Volume Knob")
        self.cb_media.SetValue(True)
        self.cb_alt = wx.CheckBox(panel, label="Enable Alt + Function Keys")
        self.cb_alt.SetValue(True)
        self.cb_shift = wx.CheckBox(panel, label="Enable Shift + Mouse Wheel")
        self.cb_shift.SetValue(True)

        vbox.Add(self.cb_media, 0, wx.ALL, 10)
        vbox.Add(self.cb_alt, 0, wx.ALL, 10)
        vbox.Add(self.cb_shift, 0, wx.ALL, 10)

        # 디바이스 선택 콤보박스
        self.device_combo = wx.ComboBox(panel, style=wx.CB_READONLY)
        devices = MiniDSPDevice.list_devices()
        for dev in devices:
            name = dev.get('product_string') or dev.get('path')
            self.device_combo.Append(name, dev.get('path'))

        if self.device_combo.GetCount() == 1:
            self.device_combo.Enable(False)
        else:
            self.device_combo.SetSelection(0)

        vbox.Add(wx.StaticText(panel, label="Select Device:"), 0, wx.LEFT | wx.TOP, 10)
        vbox.Add(self.device_combo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        panel.SetSizer(vbox)

        # 체크박스 이벤트 바인딩
        self.cb_media.Bind(wx.EVT_CHECKBOX, self.on_media_toggle)
        self.cb_alt.Bind(wx.EVT_CHECKBOX, self.on_alt_toggle)
        self.cb_shift.Bind(wx.EVT_CHECKBOX, self.on_shift_toggle)

        # 디바이스 변경 이벤트 바인딩
        self.device_combo.Bind(wx.EVT_COMBOBOX, self.on_device_changed)

    def create_tray_icon(self):
        icon = wx.Icon(wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_OTHER, (16,16)))
        self.tray = wx.adv.TaskBarIcon()
        self.tray.SetIcon(icon, "miniDSP Gain Helper")
        self.tray.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_tray_left_click)

    def on_tray_left_click(self, event):
        if self.IsShown():
            self.Hide()
        else:
            self.Show()
            self.Raise()

    def on_pause(self, event):
        logger.info("Pause hotkeys selected")
        self.hotkey_controller.pause_hotkeys()

    def on_resume(self, event):
        logger.info("Resume hotkeys selected")
        self.hotkey_controller.resume_hotkeys()

    def on_exit(self, event):
        self.Close()

    def on_close(self, event):
        self.Hide()

    def on_media_toggle(self, event):
        enabled = self.cb_media.IsChecked()
        logger.info(f"Media keys enabled: {enabled}")
        self.hotkey_controller.enable_media_keys(enabled)

    def on_alt_toggle(self, event):
        enabled = self.cb_alt.IsChecked()
        logger.info(f"Alt keys enabled: {enabled}")
        self.hotkey_controller.enable_alt_keys(enabled)

    def on_shift_toggle(self, event):
        enabled = self.cb_shift.IsChecked()
        logger.info(f"Shift keys enabled: {enabled}")
        self.hotkey_controller.enable_shift_keys(enabled)

    def on_device_changed(self, event):
        path = self.device_combo.GetClientData(self.device_combo.GetSelection())
        logger.info(f"Device changed to {path}")
        if self.controller:
            self.controller.change_device(path)
