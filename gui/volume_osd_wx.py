import wx

class VolumeOSD(wx.Frame):
    def __init__(self, *args, **kwargs):
        style = wx.FRAME_SHAPED | wx.STAY_ON_TOP | wx.NO_TASKBAR | wx.FRAME_TOOL_WINDOW
        super().__init__(None, style=style, *args, **kwargs)
        self.SetSize((260, 80))
        self.SetTransparent(200)
        self.text = ""

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Hide()

        self.timer = wx.Timer(self)
        self.timer.Bind(wx.EVT_TIMER, self.on_timer)

    def popup(self, gain):
        if gain <= -126.9:
            self.text = "Mute"
        else:
            self.text = f"Gain: {gain:.1f} dB"
        screen_size = wx.GetDisplaySize()
        self.SetPosition(((screen_size[0] - 260) // 2, 30))
        self.Show()
        self.Raise()
        self.Refresh()
        self.timer.Start(1000)  # 1초 후 자동 숨김

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        dc.SetBrush(wx.Brush(wx.Colour(0,0,0,200)))
        dc.SetPen(wx.Pen(wx.Colour(0,0,0,0)))
        dc.DrawRoundedRectangle(0, 0, 260, 80, 12)
        dc.SetTextForeground(wx.Colour(255,255,255))
        dc.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_MEDIUM))
        w, h = dc.GetTextExtent(self.text)
        dc.DrawText(self.text, (260 - w) // 2, (80 - h) // 2)

    def on_timer(self, event):
        self.Hide()
        self.timer.Stop()
