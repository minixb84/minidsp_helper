import wx

class ThemeManager:
    def __init__(self, app):
        self.app = app
        self.current = "dark"

    def apply(self, mode):
        self.current = mode
        if mode == "dark":
            self._apply_dark()
        else:
            self._apply_light()

    def _apply_dark(self):
        # 다크 모드 배경/글자색을 앱 프레임에 설정 (참고용)
        bg = wx.Colour(45, 45, 45)
        fg = wx.Colour(220, 220, 220)
        for w in wx.GetTopLevelWindows():
            w.SetBackgroundColour(bg)
            w.SetForegroundColour(fg)
            w.Refresh()

    def _apply_light(self):
        bg = wx.Colour(250, 250, 250)
        fg = wx.Colour(30, 30, 30)
        for w in wx.GetTopLevelWindows():
            w.SetBackgroundColour(bg)
            w.SetForegroundColour(fg)
            w.Refresh()
