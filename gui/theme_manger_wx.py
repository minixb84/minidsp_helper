# gui/theme_manager_wx.py
import wx

class ThemeManager:
    def __init__(self, app):
        self.app = app
        self.current = "dark"  # 기본 테마

    def apply(self, mode):
        self.current = mode
        if mode == "dark":
            self._apply_dark()
        else:
            self._apply_light()

    def _apply_dark(self):
        # wxPython 어두운 팔레트 적용
        pass

    def _apply_light(self):
        # wxPython 밝은 팔레트 적용
        pass
