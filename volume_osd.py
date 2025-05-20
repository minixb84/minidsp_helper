# volume_osd.py
# -*- coding: utf-8 -*-
"""
miniDSP Gain Helper - Volume OSD
===================================
• 다크모드 / 라이트모드 색상 다르게 표현
• 
"""
from core3 import log_exceptions, logger
from PySide6.QtCore   import QSettings, Qt, QTimer, QObject, Signal, QCoreApplication, QFile, QTextStream, qInstallMessageHandler, QtMsgType, QPoint
from PySide6.QtGui    import QPalette, QColor, QIcon, QAction, QGuiApplication, QActionGroup, QFont, QShortcut, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QApplication, QWidget, QMenu, QMenuBar, QStyleFactory, QLabel, QStyle,
    QVBoxLayout, QFormLayout, QCheckBox, QComboBox, QSystemTrayIcon, 
    QDialog, QTextEdit, QStyle, QSizePolicy, QMainWindow, QProxyStyle, QMessageBox
)

class VolumeOSD(QWidget):
    """상단 중앙 볼륨 표시 오버레이 (rounded rect + text)"""
    @log_exceptions
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowFlags(
            Qt.SplashScreen
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(260, 80)

        self._text = ""
        self._last_text = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    @log_exceptions
    def popup(self, gain: float):
        """볼륨 변경할때마다 호출"""
        self._text = "Mute" if gain <= -126.9 else f"Gain: {gain:5.1f} dB"
        
        if self._text == self._last_text:
            return
        self._last_text = self._text

        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        
        self.move(x, 30)
        self.show()
        self.raise_()
        self.update() 
        self._timer.start()

    @log_exceptions
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        bg = self.palette().color(QPalette.ToolTipBase)
        bg.setAlpha(200)

        p.setBrush(bg)        
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), 12, 12)
        p.setPen(self.palette().color(QPalette.ToolTipText))
        p.setFont(QFont("Segoe UI", 14, QFont.Medium))
        p.drawText(self.rect(), Qt.AlignCenter, self._text)
        p.end()