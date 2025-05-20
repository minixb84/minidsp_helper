# core3.py
# -*- coding: utf-8 -*-
"""
miniDSP Gain Helper - CORE
====================================================================
miniDSP Volume & Mute Control with Hotkeys + Volume Polling
• hidapi for USB HID output-reports
• 스레드 안전한 I/O (_safe_write)
• Read-Gain 스레드로 모든 키/IR 동기화
• Alt+F10/F11/F12, Media Keys 훅, USB Volume knob
• 
"""

import ctypes, threading, time, atexit, hid, logging, os, sys, functools, glob
from logging.handlers import RotatingFileHandler
from ctypes import wintypes as wt
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto
_executor = ThreadPoolExecutor(max_workers=1)
MUTE_THRESHOLD = -126.9

# ─── 로깅 설정 (프로그램 폴더 아래 logs 디렉토리 / ERROR 이상)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR  = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger('minidsp') # 로거 이름
# 환경 변수만 보고 DEBUG 모드 여부 결정
DEBUG_ENV = os.getenv('MINIDSP_DEBUG', '0') == '1'
logger.setLevel(logging.DEBUG if DEBUG_ENV else logging.ERROR)

formatter = logging.Formatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)

# ① 기존 로그(백업 포함) 삭제
for f in glob.glob(os.path.join(LOG_DIR, 'error.log*')):
    os.remove(f)

# 파일 핸들러 (회전 로테이션)
fh = RotatingFileHandler(
    os.path.join(LOG_DIR, 'error.log'),
    mode='w',                           # 매번 파일을 덮어쓰기
    maxBytes=5*1024*1024,
    backupCount=3
)
fh.setLevel(logging.DEBUG if DEBUG_ENV else logging.ERROR)
fh.setFormatter(formatter)
logger.addHandler(fh)

# 콘솔(터미널) 핸들러 추가
'''ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.WARNING)
ch.setFormatter(formatter)
logger.addHandler(ch)'''

# minidsp 로거 메시지가 루트 로거로 전파되는 것을 막음
logger.propagate = False


def log_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception("Exception in %s", func.__name__)
            raise
    return wrapper

# ─── ctypes.wintypes enhancement 
if not hasattr(wt, 'ULONG_PTR'):
    wt.ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p)==8 else wt.DWORD
if not hasattr(wt, 'LRESULT'):
    wt.LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p)==8 else ctypes.c_long

# ─── Device Discovery 
VIDS = {0x2752, 0x04D8}         # minidsp 구형 기기 0x04D8
PIDS = {0x0011, 0x0044, 0x003F} # 디락활성화 전/후

@log_exceptions
def _find_miniDSP():
    for d in hid.enumerate():
        if d['vendor_id'] in VIDS and d['product_id'] in PIDS:
            return d
    raise RuntimeError("miniDSP device not found")

@log_exceptions
def get_available_devices() -> list[dict]:
    """현재 연결된 모든 miniDSP 기기 정보(dict 리스트)를 반환"""
    return [
        d for d in hid.enumerate()
        if d['vendor_id'] in VIDS and d['product_id'] in PIDS
    ]

@log_exceptions
def set_device(path: str):
    """새 경로(path)에 해당하는 HID 디바이스로 교체"""
    global _dev, device_path
    _dev.close()
    _dev = hid.Device(path=path)
    device_path = path
    logger.info(f"Switched to device: {path}")

info = _find_miniDSP()
device_path = info['path']            # info 로부터 경로 꺼내기
_dev = hid.Device(path=info['path'])
_lock = threading.Lock()

# ─── 시작 시 한 번만 남기는 컨텍스트 로깅
logger.info(
    "App start",
    extra={
        "os": sys.platform,
        "python": sys.version.replace('\n', ' '),
        "device_path": device_path
    }
)

# ─── USB I/O Helpers
CHK = lambda *b: sum(b) & 0xFF
PAD = lambda p: b"\x00" + p.ljust(64, b"\xFF")

@log_exceptions
def _safe_write(data: bytes, retries: int=5, delay: float=0.02):
    for _ in range(retries):
        try:
            return _dev.write(data)
        except hid.HIDException as e:
            if "0x000003E5" in str(e):
                time.sleep(delay)
                continue
            raise
    return _dev.write(data)

@log_exceptions
def _read_gain_raw():
    """(dB, muted, raw_bytes) 반환"""
    with _lock:
        req = bytes([0x05,0x05,0xFF,0xDA,0x02, CHK(0x05,0x05,0xFF,0xDA,0x02)])
        _dev.write(PAD(req))
        t0 = time.time()
        while time.time() - t0 < 0.3:
            r = _dev.read(65, 50)
            if not r: continue
            if r[0] == 0: r = r[1:]
            if bytes(r[:4]) == b"\x06\x05\xFF\xDA":
                val   = r[4]
                db    = -0.5 * val
                muted = bool(r[5])
                return db, muted, bytes(r)
        raise RuntimeError("GAIN read timeout")

@log_exceptions
def _write_gain(db: float):
    with _lock:
        # flush any pending IN
        _dev.read(65, 5)
        db = max(min(db, 0.0), -127.0)
        val = int(round(-2*db))
        cmd = bytes([0x03,0x42,val, CHK(0x03,0x42,val)])
        _safe_write(PAD(cmd))

@log_exceptions
def _write_mute(toggle: bool = True):
    with _lock:
        b = 0x01 if toggle else 0x00  # True:0x01 (mute), False:0x00 (unmute)
        cmd = bytes([0x03, 0x17, b, CHK(0x03, 0x17, b)])
        _safe_write(PAD(cmd))

class Event(Enum):
    KB_VOL         = auto()
    KB_MUTE_TOGGLE = auto()
    RC_VOL         = auto()
    RC_MUTE_TOGGLE = auto()

from contextlib import contextmanager
class VolumeState:
    @log_exceptions
    def __init__(self):
        # ─── 플래그 및 상태 변수 초기화
        self.keyboard_muted    = False  # 키보드 음소거 상태 (hardware gain ≤ MUTE_THRESHOLD)
        self.digital_muted     = False  # 디지털(리모컨) 음소거 상태
        self._skip_save_only   = False  # 11번 케이스 이후 save-only 차단용 플래그
        self._ignore_poll_count = 0     # 내부 명령으로 인한 폴링 무시 카운터
        self.saved_gain = None          # saved_gain은 폴링 루프 첫 사이클에서 설정
        self._skip_next_rc_vol = False  # 다음 RC_VOL 이벤트를 무시하기 위한 플래그
        self.prev_kb  = False           # 폴링 전(토글 직전) Mute 상태 저장용
        self.prev_dig = False
        
    @contextmanager
    def suspend_polling(self):
        self._ignore_poll_count += 1        # 폴링 루프가 이 블록 내의 모든 변화를 무시하도록 카운터를 충분히 올려둠
        try:
            yield
        finally:
            self._ignore_poll_count -= 1    # 블록 종료 후에는 카운터를 내려서 다시 정상 폴링으로 복귀

    @log_exceptions
    def apply_gain(self, db: float):
        """하드웨어에 gain 쓰고 OSD 표시 (폴링 잠시 중단)"""
        with self.suspend_polling():
            _write_gain(db)
            self.show_osd(db)

    @log_exceptions
    def apply_delta(self, delta: float):
        """현재 볼륨 대비 delta만큼 조절"""
        cur, _, _ = _read_gain_raw()
        tgt = max(min(cur + delta, 0.0), -127.0)
        self.apply_gain(tgt)

    @log_exceptions
    def apply_digital_unmute(self):
        """디지털 음소거 해제 명령 보내고 내부 플래그 동기화 (폴링 잠시 중단)"""
        with self.suspend_polling():
            _write_mute(toggle=False)
        self.digital_muted = False

    @log_exceptions
    def show_osd(self, val):
        """OSD 콜백 호출 (val이 'MUTE'일 수도 있음)"""
        _gain_cb(val)

    @log_exceptions
    def current_gain(self):
        """하드웨어에서 현재 gain(dB)만 리턴받아 반환"""
        db, _, _ = _read_gain_raw()
        return db
    
    # ★★★ 모든 변수 사항을 계산한 볼륨로직 12개 적용 ★★★
    # ─── 1–3) 키보드 볼륨 UP/DOWN
    @log_exceptions
    def _kb_vol_case1(self, delta):
        # prev_kb=True AND prev_dig=False
        self.apply_gain(self.saved_gain)
        self.keyboard_muted = False 

    @log_exceptions
    def _kb_vol_case2(self, delta):
        # prev_kb=False AND prev_dig=False
        self.apply_delta(delta)                 # 볼륨 변화 적용
        self.saved_gain = self.current_gain()   # 변경된 아날로그 게인을 saved_gain에 동기화

    @log_exceptions
    def _kb_vol_case3(self, delta):
        # prev_kb=False AND prev_dig=True
        self.apply_digital_unmute()         # 디지털 음소거 비트 지우기
        self.apply_gain(self.saved_gain)    # 저장된 아날로그 게인을 다시 적용하여 장치와 OSD가 완벽하게 동기화
        self._skip_save_only = True         # 다음 원격 음소거에서 "저장 전용" 논리가 누락되지 않도록 방지

    # ─── 4–6) 키보드 음소거 토글
    @log_exceptions
    def _kb_mute_case4(self):
        # prev_kb=True AND prev_dig=False
        self.apply_gain(self.saved_gain)
        self.keyboard_muted = False

    @log_exceptions
    def _kb_mute_case5(self):
        # prev_kb=False AND prev_dig=False
        self._skip_next_rc_vol = True
        self.saved_gain = self.current_gain()
        self.apply_gain(-127.0)
        self.keyboard_muted = True 

    @log_exceptions
    def _kb_mute_case6(self):
        # prev_kb=False AND prev_dig=True
        self.apply_digital_unmute()
        self.show_osd(self.saved_gain)
        self._skip_save_only = True

    # ─── 7–9) 리모컨 볼륨 변경 감지
    @log_exceptions
    def _rc_vol_case7(self, new_db):
        # prev_kb=True AND prev_dig=False
        self.apply_gain(self.saved_gain)
        self.keyboard_muted = False

    @log_exceptions
    def _rc_vol_case8(self, new_db):
       # prev_kb=False AND prev_dig=False
       self.show_osd(new_db)    # 하드웨어는 이미 변경됨 - OSD만 갱신

    @log_exceptions
    def _rc_vol_case9(self, new_db):
        # prev_kb=False AND prev_dig=True
        self.show_osd(self.saved_gain)

    # ─── 10–12) 리모컨 뮤트 토글 감지
    @log_exceptions
    def _rc_mute_case10(self):
        # prev_kb=True AND prev_dig=False
        self.apply_digital_unmute()      
        self.apply_gain(self.saved_gain)

    @log_exceptions
    def _rc_mute_case11(self):
        # prev_kb=False AND prev_dig=False
        self.show_osd(-127.0)
        self.saved_gain = self.current_gain() 

    @log_exceptions
    def _rc_mute_case12(self):
        # prev_kb=False AND prev_dig=True
        self.show_osd(self.saved_gain)  # 12번: 저장된 볼륨정보만 OSD에 보여주기
        self._skip_save_only = True

    @log_exceptions
    def handle_event(self, event, payload=None):
        logger.debug("Handling event %s (payload=%s)", event.name, payload)

        # ─── 분기용 상태 결정
        if event in (Event.KB_VOL, Event.KB_MUTE_TOGGLE):
            # 키보드 체인지: 지금 실제 플래그를 기준
            prev_kb, prev_dig = self.keyboard_muted, self.digital_muted
        else:
            # 리모컨 체인지: 폴링 직전 상태를 기준
            prev_kb, prev_dig = self.prev_kb, self.prev_dig

        if event is Event.KB_VOL:
            if prev_kb and not prev_dig:
                self._kb_vol_case1(payload)
            elif not prev_kb and not prev_dig:
                self._kb_vol_case2(payload)
            else:
                self._kb_vol_case3(payload)
            return

        if event is Event.KB_MUTE_TOGGLE:
            if prev_kb and not prev_dig:
                self._kb_mute_case4()
            elif not prev_kb and not prev_dig:
                self._kb_mute_case5()
            else:
                self._kb_mute_case6()
            return

        # 이 플래그가 켜져 있으면 다음 RC_VOL 하나만 무시
        if  event is Event.RC_VOL and self._skip_next_rc_vol:
            self._skip_next_rc_vol = False
            logger.debug("Skipped spurious RC_VOL after KB_MUTE")
            return

        if event is Event.RC_VOL:
            if prev_kb and not prev_dig:
                self._rc_vol_case7(payload)
            elif not prev_kb and not prev_dig:
                self._rc_vol_case8(payload)
            else:
                self._rc_vol_case9(payload)
            return

        if event is Event.RC_MUTE_TOGGLE:
            if prev_kb and not prev_dig:
                self._rc_mute_case10()
            elif not prev_kb and not prev_dig and not self._skip_save_only:
                self._rc_mute_case11()
            else:
                self._rc_mute_case12()
            # save-only 차단 플래그는 한 번만 유효
            self._skip_save_only = False
            return

# ─── _poll_loop
@log_exceptions
def _poll_loop(interval: float):
    global prev_db, prev_raw

    logger.info("Poll loop started (interval=%.1f s)", interval)

    # ─── 1) 남은 IN 리포트 완전 플러시
    while True:
        try:
            buf = _dev.read(65, 5)
        except Exception:
            logger.debug("Flushed pending IN reports: exception on read")
            break
        if not buf:
            logger.debug("No pending IN reports (buffer empty)")
            break

    # ─── 2) 짧게 대기 후 안정된 첫 “유효치” 대기
    time.sleep(interval)
    while True:
        try:
            db, dig, raw = _read_gain_raw()
        except RuntimeError as e:
            logging.warning("Initial GAIN read timeout: %s", e)
            time.sleep(interval)
            continue

        if db == 0.0:
            # (DEBUG) 노이즈 판정: 0.0 dB
            logger.debug("Skipped noise report: db=0.0 dB")
            time.sleep(interval)
            continue

        logger.debug("Initial valid gain read: %.1f dB (raw=%s)", db, raw)
        break

    # ─── 3) 첫 유효치를 initial 값으로 설정하고 OSD 표시
    prev_db = db
    prev_raw = raw
    state.saved_gain = db
    logging.info("Setting initial saved_gain = %.1f dB", db)
    state.show_osd(db)

    # ─── 4) 본격 폴링 루프
    while not _stop_poll.is_set():
        time.sleep(interval)
        try:
            db, dig, raw = _read_gain_raw()
        except RuntimeError as e:
            logger.warning("Initial GAIN read timeout: %s", e)
            continue
        except Exception as e:
            logger.info("Exiting poll loop: %s", e)
            break

        # 노이즈로 간주되는 0.0 dB 리포트 건너뛰기
        if db == 0.0:
            logger.debug("Skipped noise report (0.0 dB)")
            continue

        # 내부 명령으로 인한 변화는 무시
        if state._ignore_poll_count > 0:
            logger.debug("Ignored poll (ignore_poll_count=%d)", state._ignore_poll_count)
            # 다음 사이클 오탐 방지를 위해 prev 값을 무시된 리포트로 동기화
            prev_db  = db
            prev_raw = raw
            continue

        # 상태 업데이트
        old_kb, old_dig = state.keyboard_muted, state.digital_muted
        state.keyboard_muted = (db <= MUTE_THRESHOLD)
        state.digital_muted  = bool(dig)
        # (DEBUG) 내부 상태 플래그 변동
        logger.debug("State update: kb_muted %s->%s, dig_muted %s->%s",
                     old_kb, state.keyboard_muted,
                     old_dig, state.digital_muted)

        # ── 토글 감지: 디지털 뮤트 플래그(dig) 변화가 있을 때만
        toggled = (state.digital_muted != old_dig)

        if toggled:
            state.prev_kb, state.prev_dig = old_kb, old_dig
            # prev_raw, raw 를 포맷 문자열에 넣어 줍니다
        if toggled:
            logger.info("RC_MUTE_TOGGLE event: prev_raw=%s -> raw=%s", prev_raw, raw)
            state.handle_event(Event.RC_MUTE_TOGGLE)

        elif db != prev_db:
            logger.info("RC_VOL event: %.1f dB -> %.1f dB", prev_db, db)
            # “이전” keyboard/digital mute 상태를 handle_event에 전달
            state.prev_kb, state.prev_dig = old_kb, old_dig
            state.handle_event(Event.RC_VOL, db)

        # 다음 사이클을 위해 저장
        prev_db  = db
        prev_raw = raw
        logger.debug("Updated prev_db=%.1f, prev_raw=%s", prev_db, prev_raw)

@log_exceptions
def start_polling(interval: float):
    """프로그램 시작 시 호출: 백그라운드 폴링 스레드를 띄웁니다."""
    _stop_poll.clear()
    thread = threading.Thread(target=_poll_loop, args=(interval,), daemon=True)
    thread.start()
    return thread

@log_exceptions
def stop_polling():
    """프로그램 종료 시 호출: 스레드를 멈추라고 신호를 보냅니다."""
    _stop_poll.set()

# ─── State & Callbacks
_paused      = False
_gain_cb     = lambda g: None
_media_enabled = True
_alt_enabled   = True
_shift_enabled = True
prev_db = None
prev_raw = None
prev_dig = None
WHEEL_DELTA   = 120    # Windows 1 노치 기본 델타
STEP_DB       = 0.5    # 한 노치당 볼륨 변화량(dB)
_accumulated  = 0      # 부분 델타 누적값
_stop_poll = threading.Event()
state = VolumeState()

@log_exceptions
def set_gain_callback(fn):
    global _gain_cb; _gain_cb = fn

@log_exceptions
def enable_media_keys(flag: bool):
    global _media_enabled; _media_enabled = bool(flag)

@log_exceptions
def enable_alt_keys(flag: bool):
    global _alt_enabled; _alt_enabled = bool(flag)

@log_exceptions
def enable_shift_keys(flag: bool):
    global _shift_enabled; _shift_enabled = bool(flag)

@log_exceptions
def pause_hotkeys(flag: bool):
    global _paused; _paused = bool(flag)

@log_exceptions
def step(delta):
    # 일시정지 중이면 무시
    if _paused:
        return
    # 일시정지 중이면 아무 작업도 하지 않음
    state.handle_event(Event.KB_VOL, delta)

@log_exceptions
def toggle_mute():
    # 일시정지 중이면 무시
    if _paused:
        return
    # 일시정지 중이면 아무 작업도 하지 않음
    state.handle_event(Event.KB_MUTE_TOGGLE)

# ─── Win32 Hooks
user32 = ctypes.windll.user32
WH_KEYBOARD_LL, WH_GETMESSAGE = 13, 3
WM_KEYDOWN, WM_SYSKEYDOWN = 0x0100, 0x0104
WM_APPCOMMAND = 0x0319

VK_LALT = 0xA4
VK_F10, VK_F11, VK_F12 = 0x79, 0x7A, 0x7B
VK_VOL_MUTE, VK_VOL_DOWN, VK_VOL_UP = 0xAD, 0xAE, 0xAF
APP_UP, APP_DOWN, APP_MUTE = 10, 9, 8

WH_MOUSE_LL, WM_MOUSEWHEEL, WM_MOUSEHWHEEL, VK_SHIFT, WM_MBUTTONDOWN = 14, 0x020A, 0x020E, 0x10, 0x0207

user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype  = wt.LRESULT

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('pt',        wt.POINT),
        ('mouseData', wt.DWORD),
        ('flags',     wt.DWORD),
        ('time',      wt.DWORD),
        ('dwExtraInfo', wt.ULONG_PTR),
    ]

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode',      wt.DWORD),
        ('scanCode',    wt.DWORD),
        ('flags',       wt.DWORD),
        ('time',        wt.DWORD),
        ('dwExtraInfo', wt.ULONG_PTR),
    ]

_left_alt_down = False
_hook_kb = hook_msg = None

@log_exceptions
def _kb_proc(nCode, wParam, lParam):
    global _left_alt_down
    if nCode == 0:
        k = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vk = k.vkCode
        if vk == VK_LALT:
            _left_alt_down = (wParam in (WM_KEYDOWN, WM_SYSKEYDOWN))
        elif _alt_enabled and _left_alt_down and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            if   vk == VK_F11: _executor.submit(step, +0.5);   return 1
            elif vk == VK_F10: _executor.submit(step, -0.5);    return 1
            elif vk == VK_F12: _executor.submit(toggle_mute);   return 1
            return 1
        if _media_enabled and wParam == WM_KEYDOWN:
            if   vk == VK_VOL_UP:   _executor.submit(step, +0.5);   return 1
            elif vk == VK_VOL_DOWN: _executor.submit(step, -0.5);    return 1
            elif vk == VK_VOL_MUTE: _executor.submit(toggle_mute);   return 1
    return user32.CallNextHookEx(None, nCode, wParam, lParam)

@log_exceptions
def _msg_proc(nCode, wParam, lParam):
    if nCode == 0 and _media_enabled:
        msg = ctypes.cast(lParam, ctypes.POINTER(wt.MSG)).contents
        if msg.message == WM_APPCOMMAND:
            cmd = (msg.lParam >> 16) & 0xFFF
            if   cmd == APP_UP:   _executor.submit(step, +0.5);   return 1
            elif cmd == APP_DOWN: _executor.submit(step, -0.5);    return 1
            elif cmd == APP_MUTE: _executor.submit(toggle_mute);   return 1
    return user32.CallNextHookEx(None, nCode, wParam, lParam)

@log_exceptions
def _mouse_proc(nCode, wParam, lParam):
    if nCode == 0 and _shift_enabled:
        if wParam == WM_MBUTTONDOWN and user32.GetAsyncKeyState(VK_SHIFT) < 0:
            _executor.submit(toggle_mute)
            return 1
        if wParam in (WM_MOUSEWHEEL, WM_MOUSEHWHEEL) and user32.GetAsyncKeyState(VK_SHIFT) < 0:
            ms    = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            delta = ctypes.c_short(ms.mouseData >> 16).value
            notches = delta // WHEEL_DELTA
            if notches > 0:
                _executor.submit(step, +0.5 * notches)
            elif notches < 0:
                _executor.submit(step, -0.5 * abs(notches))
            return 1
    return user32.CallNextHookEx(None, nCode, wParam, lParam)    

_KBPROC  = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wt.WPARAM, wt.LPARAM)(_kb_proc)
_MSGPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wt.WPARAM, wt.LPARAM)(_msg_proc)
_MOUSEPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wt.WPARAM, wt.LPARAM)(_mouse_proc)

@log_exceptions
def install_keyboard_hooks():
    global _hook_kb, _hook_msg, _hook_mouse
    _hook_kb  = user32.SetWindowsHookExW(WH_KEYBOARD_LL, _KBPROC, None, 0)
    _hook_msg = user32.SetWindowsHookExW(WH_GETMESSAGE, _MSGPROC, None, 0)
    _hook_mouse = user32.SetWindowsHookExW(WH_MOUSE_LL, _MOUSEPROC, None, 0)

# ─── Cleanup
@log_exceptions
def _cleanup():
    stop_polling()
    try: user32.UnhookWindowsHookEx(_hook_kb)
    except: pass
    try: user32.UnhookWindowsHookEx(_hook_msg)
    except: pass
    try: user32.UnhookWindowsHookEx(_hook_mouse)
    except: pass
    _dev.close()

atexit.register(_cleanup)