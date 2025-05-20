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
        dark_bg = wx.Colour(45, 45, 45)
        dark_fg = wx.Colour(220, 220, 220)
        palette = wx.Palette()
        palette.SetColour(wx.SYS_COLOUR_WINDOW, dark_bg)
        palette.SetColour(wx.SYS_COLOUR_WINDOWTEXT, dark_fg)
        self.app.SetPalette(palette)

    def _apply_light(self):
        light_bg = wx.Colour(250, 250, 250)
        light_fg = wx.Colour(30, 30, 30)
        palette = wx.Palette()
        palette.SetColour(wx.SYS_COLOUR_WINDOW, light_bg)
        palette.SetColour(wx.SYS_COLOUR_WINDOWTEXT, light_fg)
        self.app.SetPalette(palette)
