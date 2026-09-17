"""Foreground-only input primitives. Every action checks F8, focus and client size."""
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

    def check(self,window):
        if self.paused or self.cancelled.is_set() or self.hwnd!=window.hwnd:
            raise RuntimeError('輸入已暫停')
        r=client_rect(window.hwnd)
        if (u.GetForegroundWindow()!=window.hwnd or u.IsIconic(window.hwnd)
            or process_name(window.hwnd).lower()!='mabinogimobile.exe'
            or (r[2]-r[0],r[3]-r[1])!=BASELINE):
            self.pause('輸入前驗證失敗');raise RuntimeError(self.reason)
        vx,vy=u.GetSystemMetrics(76),u.GetSystemMetrics(77)
        if r[0]<vx or r[1]<vy or r[2]>vx+u.GetSystemMetrics(78) or r[3]>vy+u.GetSystemMetrics(79):
            self.pause('遊戲內容超出桌面');raise RuntimeError(self.reason)
        return r

    def _send(self,events):
        values=(INPUT*len(events))(*events)
        if u.SendInput(len(events),values,C.sizeof(INPUT))!=len(events):
            # Release any held key/button, never replay the action.
            for event in events:
                if event.type==1:
                    up=INPUT(1,PAYLOAD(ki=KEYBDINPUT(event.payload.ki.wVk,0,2,0,0)))
                    u.SendInput(1,C.byref(up),C.sizeof(INPUT))
            up=INPUT(0,PAYLOAD(mi=MOUSEINPUT(0,0,0,4,0,0)))
            u.SendInput(1,C.byref(up),C.sizeof(INPUT))
            self.pause('SendInput 未完整送出；禁止重試');raise RuntimeError(self.reason)

    def key(self,window,vk,control=False):
        with self.lock:
            self.check(window)
            events=[]
            def event(key,up=0):return INPUT(1,PAYLOAD(ki=KEYBDINPUT(key,0,up,0,0)))
            if control:events.append(event(0x11))
            events.extend([event(vk),event(vk,2)])
            if control:events.append(event(0x11,2))
            self._send(events)

    def click(self,window,x,y):
        with self.lock:
            rect=self.check(window)
            if not 0<=x<1280 or not 0<=y<960:raise ValueError('點擊超出遊戲內容')
            vx,vy=u.GetSystemMetrics(76),u.GetSystemMetrics(77)
            vw,vh=u.GetSystemMetrics(78),u.GetSystemMetrics(79)
            sx,sy=rect[0]+int(x),rect[1]+int(y)
            if not vx<=sx<vx+vw or not vy<=sy<vy+vh:raise ValueError('遊戲不完全位於桌面')
            dx=round((sx-vx)*65535/(vw-1));dy=round((sy-vy)*65535/(vh-1))
            self._send([INPUT(0,PAYLOAD(mi=MOUSEINPUT(dx,dy,0,0xC001,0,0))),
                        INPUT(0,PAYLOAD(mi=MOUSEINPUT(0,0,0,2,0,0))),
                        INPUT(0,PAYLOAD(mi=MOUSEINPUT(0,0,0,4,0,0)))])

    def scroll(self,window,x,y,notches):
        with self.lock:
            rect=self.check(window)
            # Move without clicking; wheel applies only to the verified foreground game.
            vx,vy=u.GetSystemMetrics(76),u.GetSystemMetrics(77)
            vw,vh=u.GetSystemMetrics(78),u.GetSystemMetrics(79)
            if not 0<=x<1280 or not 0<=y<960:raise ValueError('捲動超出遊戲內容')
            dx=round((rect[0]+x-vx)*65535/(vw-1));dy=round((rect[1]+y-vy)*65535/(vh-1))
            self._send([INPUT(0,PAYLOAD(mi=MOUSEINPUT(dx,dy,0,0xC001,0,0))),
                        INPUT(0,PAYLOAD(mi=MOUSEINPUT(0,0,(int(notches)*120)&0xffffffff,0x800,0,0)))])

    def number(self,window,value):
        if type(value) is not int or value<=0:raise ValueError('領取數量必須是正整數')
        # Select all, explicitly clear the default 1, then type the replacement.
        # Short cancellable gaps let the game's text widget process each event.
        self.key(window,0x41,control=True)
        if self.cancelled.wait(.05):raise RuntimeError('數量輸入已取消')
        self.key(window,0x08)
        if self.cancelled.wait(.05):raise RuntimeError('數量輸入已取消')
        for char in str(value):
            self.key(window,ord(char))
            if self.cancelled.wait(.05):raise RuntimeError('數量輸入已取消')

    def close(self):
        self.pause('關閉程式')
        self.closed.set()
        self.thread.join(1)
