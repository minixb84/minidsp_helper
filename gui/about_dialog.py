# gui/about_dialog.py
import wx

class AboutDialog(wx.Dialog):
    def __init__(self, parent=None):
        super().__init__(parent, title="About miniDSP Gain Helper", size=(350, 220))

        sizer = wx.BoxSizer(wx.VERTICAL)

        app_name = wx.StaticText(self, label="miniDSP Gain Helper")
        version = wx.StaticText(self, label="Version: 0.1.0")
        license_ = wx.StaticText(self, label="License: MIT License")

        font = app_name.GetFont()
        font.PointSize += 4
        font = font.Bold()
        app_name.SetFont(font)

        sizer.Add(app_name, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        sizer.Add(version, 0, wx.ALIGN_CENTER | wx.TOP, 5)
        sizer.Add(license_, 0, wx.ALIGN_CENTER | wx.TOP, 5)

        manual = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        manual.SetValue("MiniDSP 콘솔 프로그램에 단축키 설정 하나만 만들어줬어도 이런거 안만들어도 되잖아...")
        manual.SetMinSize((300, 100))

        sizer.Add(manual, 1, wx.ALL | wx.EXPAND, 10)

        btn = wx.Button(self, wx.ID_OK, label="Close")
        sizer.Add(btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        self.SetSizer(sizer)
        self.Layout()
