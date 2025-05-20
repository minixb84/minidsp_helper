# core/hotkey.py
import sys

if sys.platform.startswith("win"):
    from core.hotkey_windows import HotkeyListenerWindows as HotkeyListener
elif sys.platform == "darwin":
    from core.hotkey_macos import HotkeyListenerMacOS as HotkeyListener  # 추후 구현
elif sys.platform.startswith("linux"):
    from core.hotkey_linux import HotkeyListenerLinux as HotkeyListener  # 추후 구현
else:
    raise NotImplementedError(f"Unsupported platform: {sys.platform}")
