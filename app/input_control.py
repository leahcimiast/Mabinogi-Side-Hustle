"""Only a user-triggered I key is available. F8 and lost focus pause input."""
import ctypes as C
from ctypes import wintypes as W
import threading
from .capture import u, process_name, client_rect, BASELINE

class KEYBDINPUT(C.Structure):
    _fields_ = [('wVk',W.WORD),('wScan',W.WORD),('dwFlags',W.DWORD),('time',W.DWORD),('dwExtraInfo',C.c_size_t)]
class MOUSEINPUT(C.Structure):
    _fields_ = [('dx',W.LONG),('dy',W.LONG),('mouseData',W.DWORD),('dwFlags',W.DWORD),('time',W.DWORD),('dwExtraInfo',C.c_size_t)]
class PAYLOAD(C.Union):
    _fields_ = [('ki',KEYBDINPUT),('mi',MOUSEINPUT)]
class INPUT(C.Structure):
    _fields_ = [('type',W.DWORD),('payload',PAYLOAD)]
u.SendInput.argtypes = [W.UINT,C.POINTER(INPUT),C.c_int]
u.SendInput.restype = W.UINT

class Safety:
    def __init__(self):
        self.lock = threading.RLock()
        self.paused = True
        self.reason = '初始暫停'
        self.hwnd = None
        self.cancelled = threading.Event()
        self.closed = threading.Event()
        self.ready = threading.Event()
        self.hotkey_ok = False
        self.thread = threading.Thread(target=self._monitor,daemon=True)
        self.thread.start()
        self.ready.wait(2)

    def _monitor(self):
        self.hotkey_ok = bool(u.RegisterHotKey(None,1,0x4000,0x77))
        self.ready.set()
        try:
            msg = W.MSG()
            while not self.closed.wait(.02):
                while u.PeekMessageW(C.byref(msg),None,0,0,1):
                    if msg.message == 0x0312:
                        self.pause('F8 緊急停止')
                with self.lock:
                    if not self.paused and self.hwnd and u.GetForegroundWindow() != self.hwnd:
                        self.pause('遊戲失去焦點；請明確重新啟動測試')
        finally:
            if self.hotkey_ok:
                u.UnregisterHotKey(None,1)

    def pause(self,reason='使用者暫停'):
        with self.lock:
            self.paused,self.reason = True,reason
            self.cancelled.set()

    def prepare(self):
        with self.lock:
            self.cancelled.clear()

    def arm(self,window):
        with self.lock:
            if not self.hotkey_ok or self.cancelled.is_set():
                raise RuntimeError('熱鍵不可用或測試已取消')
            if u.GetForegroundWindow() != window.hwnd:
                raise RuntimeError('遊戲不在前景')
            self.hwnd,self.paused,self.reason = window.hwnd,False,'單次 I 測試'

    def inventory_once(self,window):
        with self.lock:
            if self.paused or self.cancelled.is_set() or self.hwnd != window.hwnd:
                raise RuntimeError('輸入已暫停')
            r=client_rect(window.hwnd)
            if (u.GetForegroundWindow()!=window.hwnd or u.IsIconic(window.hwnd)
                or process_name(window.hwnd).lower()!='mabinogimobile.exe'
                or (r[2]-r[0],r[3]-r[1])!=BASELINE):
                self.pause('輸入前驗證失敗')
                raise RuntimeError(self.reason)
            keys=(INPUT*2)(INPUT(1,PAYLOAD(ki=KEYBDINPUT(0x49,0,0,0,0))),INPUT(1,PAYLOAD(ki=KEYBDINPUT(0x49,0,2,0,0))))
            if u.SendInput(2,keys,C.sizeof(INPUT))!=2:
                release=INPUT(1,PAYLOAD(ki=KEYBDINPUT(0x49,0,2,0,0)))
                u.SendInput(1,C.byref(release),C.sizeof(INPUT))
                self.pause('SendInput 未完整送出；不重試')
                raise RuntimeError(self.reason)

    def close(self):
        self.pause('關閉程式')
        self.closed.set()
        self.thread.join(1)
