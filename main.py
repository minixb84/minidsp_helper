# main.py
# -*- coding: utf-8 -*-
"""
miniDSP Gain Helper - GUI
===================================
• 트레이 아이콘, 툴팁, 창 아이콘 모두 APP_NAME 사용
• 미디어키 / Alt / Shift 단축키 토글
• 메뉴아이템 Pause/Resume/Light Mode/Dark Mode/About
• 예정: 단축키 지정, 입력소스 선택, 프리셋 선택, 볼륨프리셋&단축키지정 3개(음악, 영화 등...)
• 
"""
from __future__ import annotations
import sys, logging, argparse, os, ctypes, platform, re
import core3 as core
from ctypes import wintypes
from pathlib import Path
from volume_osd import VolumeOSD
from core3 import log_exceptions, logger
from theme_manager import ThemeManager, set_window_dark_titlebar
from PySide6.QtCore   import QSettings, Qt, QTimer, QObject, Signal, QCoreApplication, QFile, QTextStream, qInstallMessageHandler, QtMsgType, QPoint
from PySide6.QtGui    import QPalette, QColor, QIcon, QAction, QGuiApplication, QActionGroup, QFont, QShortcut, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QApplication, QWidget, QMenu, QMenuBar, QStyleFactory, QLabel, QStyle,
    QVBoxLayout, QFormLayout, QCheckBox, QComboBox, QSystemTrayIcon, 
    QDialog, QTextEdit, QStyle, QSizePolicy, QMainWindow, QProxyStyle, QMessageBox
)

# argparse 로 --debug 옵션 받기
parser = argparse.ArgumentParser()
parser.add_argument(
    '--debug', action='store_true',
    help='Enable debug logging (overrides MINIDSP_DEBUG env var)'
)
args = parser.parse_args()

# 1) CLI --debug 우선, 없으면 환경변수
debug = args.debug or (os.getenv('MINIDSP_DEBUG','0') == '1')
# 2) 로거 기본 레벨
logger.setLevel(logging.DEBUG if debug else logging.ERROR)
# 3) 기존에 등록된 핸들러들에도 똑같이 적용
for h in logger.handlers:
    h.setLevel(logging.DEBUG if debug else logging.ERROR)
# minidsp 로거가 더 이상 루트로 메시지 전파하지 않도록
logger.propagate = False

# ─── 클래스 정의
class IRBridge(QObject):
    gainChanged = Signal(float)

APP_NAME  = "miniDSP Gain Helper"
APP_VERSION = "0.1.0"
ICON_PATH = Path(__file__).with_suffix('.ico')
    
class MenuBarStyle(QProxyStyle):
    def pixelMetric(self, metric, option=None, widget=None):
        if metric in (
            QStyle.PM_MenuBarItemSpacing,
            QStyle.PM_MenuBarHMargin,
            QStyle.PM_MenuBarVMargin,
            QStyle.PM_MenuBarPanelWidth
        ):
            return 0
        return super().pixelMetric(metric, option, widget)


# ─── About 대화상자
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About")

        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        layout = QVBoxLayout(self)

        for text in (
            APP_NAME,
            f"Version: {APP_VERSION}",
            "License: MIT License",
        ):
            lbl = QLabel(text)
            layout.addWidget(lbl)

        # 개발자 한마디
        self.manual = QTextEdit()
        self.manual.setReadOnly(True)
        self.manual.setPlainText("MiniDSP콘솔 프로그램에 단축키 설정 하나만 만들어줬어도 이런거 안만들어 되잖아...")
        self.manual.setFixedHeight(90)
        layout.addWidget(self.manual)

    def showEvent(self, event):
        super().showEvent(event)
        # 1) 부모(MainWindow)의 ThemeManager에서 현재 테마 읽기
        from PySide6.QtCore import QSettings
        parent = self.parent()
        if parent and hasattr(parent, 'theme_mgr'):
            is_dark = (parent.theme_mgr.current == 'dark')
        else:
            # 부모가 없거나 ThemeManager가 없으면, QSettings에 저장된 값 사용
            settings = QSettings("MyCompany", "miniDSP Gain Helper")
            is_dark = (settings.value("theme", "dark") == "dark")        

        # 2) 비클라이언트(타이틀바) 다크/라이트 모드 동기화
        set_window_dark_titlebar(int(self.winId()), is_dark)

        # 3) 다이얼로그 크기 조정
        self.adjustSize()

        if self.parent():
            # 부모 윈도우 전체 프레임(타이틀바+테두리 포함)
            parent_frame = self.parent().frameGeometry()
            # 다이얼로그 전체 프레임
            dlg_frame = self.frameGeometry()
            # 부모 중앙에 다이얼로그 중앙이 맞춰지도록
            dlg_frame.moveCenter(parent_frame.center())
            # 계산된 좌상단으로 이동
            self.move(dlg_frame.topLeft())

#=============================
class MainWindow(QMainWindow):
    @log_exceptions
    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    @log_exceptions
    def __init__(self, osd: VolumeOSD):
        super().__init__()
        self.theme_mgr = ThemeManager(QApplication.instance())

        # ─── GUI 실시간 확인용 
        self._reload_qss_sc = QShortcut(QKeySequence("F5"), self,activated=lambda: self.theme_mgr.reload_qss(window=self))
        # ───────────────────────────────────

        # ─── (1) 프레임리스 + 기본 설정
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowSystemMenuHint
            | Qt.WindowCloseButtonHint
        )
        self.osd = osd
        self.setWindowTitle(APP_NAME)

        # ─── (2) 드래그용 변수
        self._drag_pos = None

        # ─── (4) 공통 액션 정의
        self.action_show  = QAction("Show", self, triggered=self._show_window)
        pause_group = QActionGroup(self)
        pause_group.setExclusive(True)
        self.pause_act  = QAction("Pause",  self, checkable=True)
        self.resume_act = QAction("Resume", self, checkable=True)
        pause_group.addAction(self.pause_act)
        pause_group.addAction(self.resume_act)
        self.resume_act.setChecked(True)
        action_exit = QAction("Exit",   self, triggered=QApplication.quit)

        self.pause_act.triggered.connect(lambda _: (core.pause_hotkeys(True), self._refresh_info()))
        self.resume_act.triggered.connect(lambda _: (core.pause_hotkeys(False), self._refresh_info()))
        
        # ─── (5) 트레이 아이콘 & 메뉴
        icon = QIcon(str(ICON_PATH)) if ICON_PATH.exists() else self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip(APP_NAME)

        tray_menu = QMenu()
        tray_menu.setAttribute(Qt.WA_StyledBackground, True)
        tray_menu.addActions([self.action_show, self.pause_act, self.resume_act])
        tray_menu.addSeparator()
        tray_menu.addAction(action_exit)
        self.tray.setContextMenu(tray_menu)
        self.tray.show()
        self.tray.activated.connect(
            lambda reason: self._show_window() if reason == QSystemTrayIcon.Trigger else None
        )

        # ─── (6) 메뉴바 생성·스타일·액션 추가
        # QMenuBar를 MainWindow(self)를 부모로 생성하고, 바로 메뉴바로 설정
        self.menu_bar = QMenuBar(self)
        # QSS가 적용된 background-color가 보이도록
        self.menu_bar.setAttribute(Qt.WA_StyledBackground, True)
        # 내부 레이아웃의 마진·간격을 0으로
        self.menu_bar.setContentsMargins(0, 0, 0, 0)
        if self.menu_bar.layout():
            self.menu_bar.layout().setContentsMargins(0, 0, 0, 0)
            self.menu_bar.layout().setSpacing(0)
      
        self.menu_bar.setMouseTracking(True)
        self.setMenuBar(self.menu_bar)
        self.menu_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        file_menu = self.menu_bar.addMenu("&File")
        file_menu.setAttribute(Qt.WA_StyledBackground, True)
        file_menu.addActions([self.pause_act, self.resume_act])
        file_menu.addSeparator()
        file_menu.addAction(action_exit)

        # Theme 메뉴
        theme_menu = self.menu_bar.addMenu("&Theme")
        theme_menu.setAttribute(Qt.WA_StyledBackground, True)
        group = QActionGroup(self)

        #group.setExclusive(True)
        self.light_act = QAction("Light Mode", self, checkable=True)
        self.dark_act  = QAction("Dark Mode",  self, checkable=True)
        group.addAction(self.light_act)
        group.addAction(self.dark_act)
        theme_menu.addActions([self.light_act, self.dark_act])
        # 이전에 저장된 테마 불러오기
        if self.theme_mgr.current == "dark":
            self.dark_act.setChecked(True)
        else:
            self.light_act.setChecked(True)
        # MainWindow 자신(self)을 넘겨서 타이틀바 동기화까지 보장
        self.theme_mgr.apply(self.theme_mgr.current, window=self)
        # 연결
        self.light_act.triggered.connect(lambda: self.theme_mgr.apply("light", window=self))
        self.dark_act.triggered.connect(lambda: self.theme_mgr.apply("dark",  window=self))       

        help_menu = self.menu_bar.addMenu("&Help")
        help_menu.setAttribute(Qt.WA_StyledBackground, True)
        help_menu.addAction("About", self._show_about_dialog)

        # 상태 메시지 메뉴 - QSS 폰트색상을 위해 변경 테스트
        self.status_menu = self.menu_bar.addMenu("Unknown")
        self.status_menu.setEnabled(False)
        self._refresh_info()

        # ─── 중앙 위젯 + 레이아웃
        central = QWidget(self)
        layout  = QVBoxLayout(central)

        # ─── (7) 기존 UI 위젯들 생성 & 레이아웃 배치 코드 삽입
        # 7-1) Media Keys 체크박스 & 설명
        self.cb_media   = QCheckBox("Media Keys ＆ Volume knob",
                                    checked=True,
                                    toggled=self._apply_hotkey_state)
        self.media_desc = QLabel("  🔊⬆️  🔉⬇️  🔇🚫") #  🎚️
        self.media_desc.setIndent(
            self.cb_media.fontMetrics().horizontalAdvance(self.cb_media.text()[0])
        )
        # 7-2) Alt+F10/F11/F12 체크박스 & 설명
        self.cb_alt   = QCheckBox("Alt + Function Keys",
                                checked=True,
                                toggled=self._apply_hotkey_state)
        self.alt_desc = QLabel("    F10⬆️ F11⬇️ F12🚫") # + alt⌨️
        self.alt_desc.setIndent(
            self.cb_alt.fontMetrics().horizontalAdvance(self.cb_alt.text()[0])
        )
        # 7-3) Mosue + Wheel Up/Down 체크박스 & 설명
        self.cb_shift   = QCheckBox("Shift + Mouse Wheel",
                                checked=True,
                                toggled=self._apply_hotkey_state)
        self.shift_desc = QLabel("    UP⬆️ Down⬇️ Click🚫") # + Shift⌨️
        self.shift_desc.setIndent(
            self.cb_shift.fontMetrics().horizontalAdvance(self.cb_shift.text()[0])
        )
        # layout에 추가
        layout.addWidget(self.cb_media)
        layout.addWidget(self.media_desc)
        layout.addSpacing(5)
        layout.addWidget(self.cb_alt)
        layout.addWidget(self.alt_desc)
        layout.addSpacing(5) 
        layout.addWidget(self.cb_shift)
        layout.addWidget(self.shift_desc)
        layout.addSpacing(10) 

        # 7-4) Polling interval (QFormLayout)
        form = QFormLayout()
        self.lbl_poll = QLabel("Polling interval:")
  
        # 반드시 콤보박스 생성 먼저
        self.cb_poll = QComboBox()
        self.cb_poll.setFixedWidth(130)
        self.cb_poll.setFixedHeight(25)
        for label, val in [("50 ms", 0.05),
                        ("100 ms", 0.1),
                        ("200 ms", 0.2),
                        ("500 ms", 0.5)]:
            self.cb_poll.addItem(label, val)
        idx = self.cb_poll.findData(0.1)
        if idx >= 0:
            self.cb_poll.setCurrentIndex(idx)
        self.cb_poll.currentIndexChanged.connect(self._on_poll_interval_changed)
        form.addRow(self.lbl_poll, self.cb_poll)
        layout.addLayout(form)      

        # 7-5) Device (QFormLayout)
        form = QFormLayout()
        lbl_dev = QLabel("Device:             ")
        self.cb_device = QComboBox()
        self.cb_device.setFixedWidth(130)
        self.cb_device.setFixedHeight(25)        

        # core3.get_available_devices() 로 실제 기기 리스트 조회
        devices = core.get_available_devices()
        for info in devices:
            # 사용자에게 보여줄 이름 예시: 제품명
            name = info.get('product_string', info['path'])
            self.cb_device.addItem(name, info['path'])

        # 기기가 1개면 선택 불필요 - 콤보박스 비활성화
        if self.cb_device.count() == 1:
            self.cb_device.setEnabled(False)
        else:
            # 다중일 땐 첫 스캔된 제품이 기본
            self.cb_device.setCurrentIndex(0)

        # 선택 변경 시 콜백
        self.cb_device.currentIndexChanged.connect(self._on_device_changed)
        form.addRow(lbl_dev, self.cb_device)
        layout.addLayout(form)      

        # 7-6) 남은 공간 채우기
        layout.addStretch(1)
        self.setCentralWidget(central)  # 중앙 위젯으로 설정
        self.setFixedSize(250, 290)     # 주석처리하면 알아서 맞춰짐

    # ─── 핫키 토글
    @log_exceptions
    def _apply_hotkey_state(self, checked: bool):
        # 체크박스 토글 시 설명 라벨 보임/숨김, 필요없을 듯
        #self.media_desc.setVisible(self.cb_media.isChecked())
        #self.alt_desc.setVisible(self.cb_alt.isChecked())
        #self.shift_desc.setVisible(self.cb_shift.isChecked())
        # 핫키 체크박스상태에 따라 활성/비활성
        core.enable_media_keys(self.cb_media.isChecked())
        core.enable_alt_keys(self.cb_alt.isChecked())
        core.enable_shift_keys(self.cb_shift.isChecked())
        self._refresh_info() # 상태(Active/Paused) 갱신

    @log_exceptions
    def _show_about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec()

    # ─── 정보 라벨
    @log_exceptions
    def _refresh_info(self):
        state = 'Paused' if self.pause_act.isChecked() else 'Active'
        self.status_menu.setTitle(f"{state}")
    
    @log_exceptions
    def closeEvent(self, e):
        e.ignore(); self.hide()

    @log_exceptions
    def _on_poll_interval_changed(self, index: int):
        """콤보박스에서 폴링 간격을 바꾸면, 백그라운드 폴링을 재시작."""
        interval = self.cb_poll.itemData(index)
        core.stop_polling()             # 기존 폴링 중지
        core.start_polling(interval)    # 새 간격으로 시작
        # 상태 라벨이나 로그에 찍어줌
        logger.info(f"Polling interval changed to {interval:.3f} s")

    @log_exceptions
    def _on_device_changed(self, index: int):
        path = self.cb_device.itemData(index)
        core.set_device(path)                           # core 쪽 디바이스 교체
        core.stop_polling()                             # 폴링 스레드 재시작
        core.start_polling(self.cb_poll.currentData())
        self._refresh_info()                            # 상태바 갱신

    @log_exceptions
    def showEvent(self, event):
        super().showEvent(event)
        win_handle = self.windowHandle()    # 프레임 핸들 얻기
        if win_handle is not None:
            hwnd = int(win_handle.winId())
        else:
            hwnd = int(self.winId())
        set_window_dark_titlebar(
            hwnd,
            self.theme_mgr.current == "dark"
        )

        # 화면 중앙으로
        screen = self.screen() or QGuiApplication.primaryScreen()
        center_point = screen.availableGeometry().center()
        frame_geom = self.frameGeometry()
        frame_geom.moveCenter(center_point)
        self.move(frame_geom.topLeft())

@log_exceptions
def main():
    app = QApplication(sys.argv)                    # QApplication, OSD, Bridge, MainWindow 순서로 생성    
    #app.setAttribute(Qt.AA_DontUseNativeMenuBar)   # macOS native 메뉴바 비활성화 (mac 필수: 확인필요)
    osd = VolumeOSD()
    bridge = IRBridge()
    bridge.gainChanged.connect(osd.popup)           # 브리지로 OSD.popup을 호출 연결
    
    core.set_gain_callback(bridge.gainChanged.emit) # core에 콜백 등록 
    core.enable_media_keys(True)                    # Media키
    core.enable_alt_keys(True)                      # Alt키
    core.enable_shift_keys(True)                    # Shift키
    core.start_polling(0.1)                         # 0.1초 minidsp 모니터 시작
    core.install_keyboard_hooks()                   # 키보드 훅 Alt키, Media키, Shift키

    win = MainWindow(osd)
    win.show()
    
    app.aboutToQuit.connect(core.stop_polling)
    sys.exit(app.exec())


#===========================
if __name__ == "__main__":
    main()
    
    