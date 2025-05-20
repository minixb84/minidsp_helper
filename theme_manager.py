# theme_manager.py
# -*- coding: utf-8 -*-
"""
miniDSP Gain Helper - Themes
===================================
• 
• 
"""
import ctypes, platform
from ctypes import wintypes
from pathlib import Path
from core3 import log_exceptions, logger
from PySide6.QtCore   import QSettings, Qt, QTimer, QObject, Signal, QCoreApplication, QFile, QTextStream, qInstallMessageHandler, QtMsgType, QPoint
from PySide6.QtGui    import QPalette, QColor, QIcon, QAction, QGuiApplication, QActionGroup, QFont, QShortcut, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QApplication, QWidget, QMenu, QMenuBar, QStyleFactory, QLabel, QStyle,
    QVBoxLayout, QFormLayout, QCheckBox, QComboBox, QSystemTrayIcon, 
    QDialog, QTextEdit, QStyle, QSizePolicy, QMainWindow, QProxyStyle, QMessageBox
)

#--- 오류 검증용 개발후 삭제
_qss_warnings: list[str] = []           # 앱 전역 경고 버퍼

@log_exceptions
def _style_msg_handler(msg_type, context, msg):
    if msg_type == QtMsgType.QtWarningMsg and "stylesheet" in msg.lower():
        _qss_warnings.append(msg)       # 일단 저장만
        print(msg)                      # 콘솔엔 즉시 출력
#--- 오류 검증용 개발후 삭제

THEME_DIR = Path(__file__).with_name("themes")

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19 # Windows 10 1809~1909 : 윈도우10 사용자는 최소 1809버전부터 사용가능

if platform.system() == "Windows":
    _IsWindow = ctypes.windll.user32.IsWindow
    _IsWindow.argtypes = [wintypes.HWND]
    _IsWindow.restype  = wintypes.BOOL

@log_exceptions
def set_window_dark_titlebar(hwnd: int, enable: bool = True):
    """
    hwnd: Qt 창 핸들 (int(self.winId()))
    enable: True 면 다크, False 면 라이트
    """
    if platform.system() != "Windows":
        return
    val = wintypes.BOOL(enable)
    for attr in (20, 19):
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            ctypes.c_uint(attr),
            ctypes.byref(val),
            ctypes.sizeof(val)
        )
    # 비클라이언트(타이틀바/테두리) 강제 리프레시
    SWP_FLAGS = 0x0001 | 0x0002 | 0x0004 | 0x0020
    ctypes.windll.user32.SetWindowPos(
        wintypes.HWND(hwnd), None, 0,0,0,0, SWP_FLAGS
    )

class ThemeManager(QObject):
    @log_exceptions
    def __init__(self, app):
        super().__init__(app)  # parent=app
        self.app = app

        # 앱에 이미 설치됐는지 체크 — 중복 방지: 오류테스트용 개발 후 삭제
        if not hasattr(app, "_qss_msg_hook"):
            qInstallMessageHandler(_style_msg_handler)
            app._qss_msg_hook = True
        # 앱에 이미 설치됐는지 체크 — 중복 방지: 오류테스트용 개발 후 삭제

        self.settings = QSettings("MyCompany", "miniDSP Gain Helper")
        self.current = self.settings.value("theme", "dark") or "dark"

        # ─── 최초 한 번만 Fusion 스타일로 고정
        # 
        if app.style().objectName().lower() != "fusion":
            app.setStyle(QStyleFactory.create("Fusion"))

        # ─── 메뉴가 닫힌 뒤 한 번만 타이틀바·메뉴를 갱신하기 위한 토큰
        self._pending_refresh : tuple[QWidget,bool] | None = None
        self.app.focusWindowChanged.connect(self._on_focus_back)

    # ────────────────────────────────────────────────
    @log_exceptions
    def _clear_menu_styles(self):
        """위젯에 달려 있던 개별 QStyle을 제거해 전역 스타일을 상속"""
        for w in self.app.allWidgets():
            if isinstance(w, (QMenuBar, QMenu)):
                w.setStyle(None)           # 개별 스타일 해제

    @log_exceptions
    def apply(self, mode: str, window=None):
        """mode: 'dark' or 'light'"""
        self.current = mode
        self.settings.setValue("theme", mode)

        # ── 1) 팔레트 · QSS 즉시 적용 ─────────────────────
        if mode == "dark":
            self._apply_dark_palette()
            self._apply_qss(self._dark_qss())
        else:
            self._apply_light_palette()
            self._apply_qss(self._light_qss())

        # ── 2) 스타일은 고정됐으므로 더 할 일 없음 ──────────────
        if window is not None:
            self._pending_refresh = (window, mode == "dark")
            if window.isActiveWindow():
                self._finalize_refresh()

    #──────── 내부 콜백들 ───────────────────────────────────────────────
    @log_exceptions
    def _on_focus_back(self, win):
        """메뉴가 닫혀 메인 창이 다시 포커스를 얻는 순간"""
        if self._pending_refresh:
            pending_widget, _ = self._pending_refresh
            # focusWindowChanged 는 QWindow 를 주므로 둘 모두 비교
            if  win == pending_widget or \
                win == getattr(pending_widget, "windowHandle", lambda: None)():
                self._finalize_refresh()

    @log_exceptions
    def _finalize_refresh(self):       
        window, dark = self._pending_refresh
        self._refresh_menus() # 메뉴 re-polish (팔레트만 새로 먹이면 끝)
        # 타이틀바
        set_window_dark_titlebar(int(window.windowHandle().winId()), dark)
        self._pending_refresh = None

    @log_exceptions
    def _refresh_menus(self):
        """이미 생성된 QMenu/QMenuBar가 새 팔레트를 쓰도록 재-polish"""
        for w in self.app.allWidgets():
            # 1) 메뉴바 ───────────────
            if isinstance(w, QMenuBar):
                w.setPalette(QPalette())          # 새 팔레트 적용
                w.update()

            # 2) 드롭다운 메뉴(QMenu) ──
            elif isinstance(w, QMenu):
                w.setPalette(QPalette())          # 새 팔레트 적용
                w.setStyle(self.app.style())      # 전역 스타일 공유
                w.update()

            # 3) 그 밖의 위젯은 건드리지 않음      

    @log_exceptions
    def _apply_dark_palette(self):
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(45,45,45))
        pal.setColor(QPalette.WindowText, QColor(220,220,220))
        pal.setColor(QPalette.Base, QColor(30,30,30))
        pal.setColor(QPalette.AlternateBase, QColor(53,53,53))
        pal.setColor(QPalette.Dark,  QColor(25,25,25))
        pal.setColor(QPalette.Light, QColor(70,70,70))
        pal.setColor(QPalette.Mid,   QColor(60,60,60))
        pal.setColor(QPalette.ToolTipBase, QColor(60,60,60))
        pal.setColor(QPalette.ToolTipText, QColor(255,255,255))
        pal.setColor(QPalette.Text, QColor(220,220,220))
        pal.setColor(QPalette.Button, QColor(53,53,53))
        pal.setColor(QPalette.ButtonText, QColor(220,220,220))
        pal.setColor(QPalette.Highlight, QColor(100,100,100))
        pal.setColor(QPalette.HighlightedText, QColor(255,255,255))
        self.app.setPalette(pal)

    @log_exceptions
    def _apply_light_palette(self):
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(250,250,250))
        pal.setColor(QPalette.WindowText, QColor(30,30,30))
        pal.setColor(QPalette.Base, QColor(255,255,255))
        pal.setColor(QPalette.AlternateBase, QColor(240,240,240))
        pal.setColor(QPalette.Dark,  QColor(160,160,160))
        pal.setColor(QPalette.Light, QColor(255,255,255))
        pal.setColor(QPalette.Mid,   QColor(200,200,200))
        pal.setColor(QPalette.ToolTipBase, QColor(255,255,225))
        pal.setColor(QPalette.ToolTipText, QColor(30,30,30))
        pal.setColor(QPalette.Text, QColor(30,30,30))
        pal.setColor(QPalette.Button, QColor(240,240,240))
        pal.setColor(QPalette.ButtonText, QColor(30,30,30))
        pal.setColor(QPalette.Highlight, QColor(0,120,215))
        pal.setColor(QPalette.HighlightedText, QColor(255,255,255))
        self.app.setPalette(pal)

    @log_exceptions
    def _apply_qss(self, qss: str):
        self.app.setStyleSheet(qss)

    @log_exceptions
    def _dark_qss(self) -> str:
        return (THEME_DIR / "dark.qss").read_text(encoding="utf-8")

    @log_exceptions
    def _light_qss(self) -> str:
        return (THEME_DIR / "light.qss").read_text(encoding="utf-8")

    @log_exceptions
    def _apply_titlebar(self, dark: bool):
        win = self.app.activeWindow() # activeWindow()가 없으면 바로 리턴
        if not win:
            return
        set_window_dark_titlebar(int(win.winId()), dark)


    # ──────GUI개발용──────────────────────────────────────────────────────
    @log_exceptions
    def reload_qss(self, window: QWidget | None = None) -> None:
        """
        QSS만 다시 입힌다.
        - 팔레트는 건드리지 않고,
        - 현재 theme(self.current)에 맞춰 _dark_qss / _light_qss를 갱신.
        핫-리로드용 단축키(Ctrl-R)에서 호출한다.
        """
        # QSS 새로 적용
        self._apply_qss(self._dark_qss() if self.current == "dark"
                                          else self._light_qss())

        # 이미 떠-있는 메뉴바·드롭다운을 다시 polish
        self._refresh_menus()

        # 창을 넘기면 타이틀바·클라이언트 영역까지 repaint
        if window:
            window.repaint()

        # 경고 모아둔 게 있으면 한 번에 보여 주기 : 오류검증용 개발 후 삭제
        if _qss_warnings:
            QMessageBox.warning(
                window or None,
                "QSS 파싱 경고",
                "\n".join(_qss_warnings)
            )
            _qss_warnings.clear()
    # ──────GUI개발용──────────────────────────────────────────────────────