"""Foreground-only input primitives. Every action checks F8, focus and client size."""
import ctypes as C
from ctypes import wintypes as W
import threading
import queue
import time
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
    def __init__(self, hotkey="F8"):
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.user_paused = False
        self.running = False
        self.paused_seconds = 0.0
        self.pause_started = None
        self.on_hotkey = lambda event: None
        self.hotkey_name = hotkey if hotkey in {f'F{i}' for i in range(1,13)} else 'F8'
        self.rebind_requests = queue.Queue()
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
        hotkey_id=1
        self.hotkey_ok = bool(u.RegisterHotKey(None,hotkey_id,0x4000,0x6F+int(self.hotkey_name[1:])))
        self.ready.set()
        try:
            msg = W.MSG()
            while not self.closed.wait(.02):
                while not self.rebind_requests.empty():
                    name,result,done=self.rebind_requests.get()
                    new_id=2 if hotkey_id==1 else 1
                    ok=bool(u.RegisterHotKey(None,new_id,0x4000,0x6F+int(name[1:])))
                    if ok:
                        if self.hotkey_ok:u.UnregisterHotKey(None,hotkey_id)
                        hotkey_id=new_id;self.hotkey_name=name;self.hotkey_ok=True
                    result.append(ok);done.set()
                while u.PeekMessageW(C.byref(msg),None,0,0,1):
                    if msg.message == 0x0312 and msg.wParam==hotkey_id:
                        if self.user_paused:self.on_hotkey('resume')
                        elif self.running and not self.cancelled.is_set():
                            self.suspend();self.on_hotkey('paused')
                with self.lock:
                    if not self.paused and self.hwnd and u.GetForegroundWindow() != self.hwnd:
                        self.pause('遊戲失去焦點；請明確重新啟動測試')
        finally:
            if self.hotkey_ok:
                u.UnregisterHotKey(None,hotkey_id)

    def rebind(self, name):
        if name not in {f'F{i}' for i in range(1,13)}:raise ValueError('請選擇 F1 至 F12。')
        if name==self.hotkey_name and self.hotkey_ok:return True
        result=[];done=threading.Event()
        self.rebind_requests.put((name,result,done))
        if not done.wait(2):raise RuntimeError('熱鍵設定逾時，請重新開啟程式。')
        return result[0]

    def suspend(self):
        with self.condition:
            if self.cancelled.is_set():return
            if not self.user_paused:self.pause_started=time.monotonic()
            self.user_paused=True;self.paused=True;self.reason='使用者暫停'

    def resume(self, window):
        with self.condition:
            if not self.user_paused:raise RuntimeError('目前並非手動暫停。')
            self.arm(window)
            if self.pause_started is not None:self.paused_seconds+=time.monotonic()-self.pause_started
            self.pause_started=None;self.user_paused=False
            self.condition.notify_all()

    def pause(self,reason='使用者暫停'):
        with self.lock:
            self.paused,self.reason = True,reason
            self.cancelled.set()
            self.running=False
            self.user_paused=False
            self.condition.notify_all()

    def prepare(self):
        with self.lock:
            self.cancelled.clear()
            self.running=True

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

    def wait_if_paused(self):
        with self.condition:
            while self.user_paused and not self.cancelled.is_set():self.condition.wait(.1)

    def check(self,window):
        self.wait_if_paused()
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

    def drag(self,window,start,end):
        """A short horizontal swipe, always releasing the button on cancellation."""
        if any(not 0<=x<1280 or not 0<=y<960 for x,y in (start,end)):
            raise ValueError('拖曳超出遊戲內容')
        def movement(x,y):
            rect=self.check(window)
            vx,vy=u.GetSystemMetrics(76),u.GetSystemMetrics(77)
            vw,vh=u.GetSystemMetrics(78),u.GetSystemMetrics(79)
            dx=round((rect[0]+x-vx)*65535/(vw-1));dy=round((rect[1]+y-vy)*65535/(vh-1))
            return INPUT(0,PAYLOAD(mi=MOUSEINPUT(dx,dy,0,0xC001,0,0)))
        # Finish this short mouse gesture before a resumable pause; never leave
        # the mouse held while waiting for the player to resume.
        with self.lock:
            with self.lock:self.check(window)
            try:
                with self.lock:
                    self._send([movement(*start),INPUT(0,PAYLOAD(mi=MOUSEINPUT(0,0,0,2,0,0)))])
                for step in range(1,13):
                    if self.cancelled.wait(.025):raise RuntimeError('拖曳已暫停')
                    with self.lock:
                        self._send([movement(start[0]+(end[0]-start[0])*step/12,start[1]+(end[1]-start[1])*step/12)])
            finally:
                # Release even after F8/focus loss; never leave a held mouse button.
                with self.lock:self._send([INPUT(0,PAYLOAD(mi=MOUSEINPUT(0,0,0,4,0,0)))])

    def number(self,window,value):
        if type(value) is not int or value<=0:raise ValueError('領取數量必須是正整數')
        # Select all, explicitly clear the default 1, then type the replacement.
        # Short cancellable gaps let the game's text widget process each event.
        self.key(window,0x41,control=True)
        if self.cancelled.wait(.15):raise RuntimeError('數量輸入已取消')
        self.key(window,0x08)
        if self.cancelled.wait(.15):raise RuntimeError('數量輸入已取消')
        for char in str(value):
            self.key(window,ord(char))
            if self.cancelled.wait(.15):raise RuntimeError('數量輸入已取消')

    def close(self):
        self.pause('關閉程式')
        self.closed.set()
        self.thread.join(1)
