# gui/main_wx.py
import wx
import logging

logger = logging.getLogger("minidsp.gui")

class MainFrame(wx.Frame):
    def __init__(self, volume_osd, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.volume_osd = volume_osd

        self.SetTitle("miniDSP Gain Helper")
        self.SetSize((300, 350))
        self.Center()

        self.create_menu()
        self.create_controls()
        self.create_tray_icon()

    def create_menu(self):
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        pause_item = file_menu.Append(wx.ID_ANY, "Pause")
        resume_item = file_menu.Append(wx.ID_ANY, "Resume")
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

        # 체크박스 등 필요한 위젯 생성 및 배치

        panel.SetSizer(vbox)

    def create_tray_icon(self):
        # 트레이 아이콘 생성 및 이벤트 바인딩 구현
        pass

    def on_pause(self, event):
        logger.info("Pause clicked")

    def on_resume(self, event):
        logger.info("Resume clicked")

    def on_exit(self, event):
        self.Close()
