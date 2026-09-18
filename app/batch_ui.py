"""Automatic game validation used by the single-window dashboard."""
from . import capture

def prepare_game(safety):
    safety.wait_if_paused()
    windows=capture.detect()
    if len(windows)!=1:
        raise RuntimeError(f'找到 {len(windows)} 個遊戲視窗；請只保留一個瑪奇 Mobile 視窗。')
    window=windows[0]
    capture.capture(window)  # Automatically verify foreground, size and usable content.
    safety.arm(window)
    safety.check(window)
    return window


def focus_game(safety):
    """One foreground request at user-triggered startup; never retry during work."""
    from ctypes import wintypes as W
    if safety.cancelled.is_set():
        raise RuntimeError(safety.reason)
    if not safety.hotkey_ok:
        raise RuntimeError('暫停熱鍵不可用；無法開始。')
    windows=capture.detect()
    if len(windows)!=1:
        raise RuntimeError(f'找到 {len(windows)} 個遊戲視窗；請只保留一個瑪奇 Mobile 視窗。')
    window=windows[0]
    if capture.process_name(window.hwnd).lower()!='mabinogimobile.exe':
        raise RuntimeError('無法確認遊戲視窗；已停止。')
    capture.u.ShowWindow.argtypes=[W.HWND, W.INT]
    capture.u.SetForegroundWindow.argtypes=[W.HWND]
    if safety.cancelled.is_set():raise RuntimeError(safety.reason)
    if capture.u.IsIconic(window.hwnd):capture.u.ShowWindow(window.hwnd,9)
    capture.u.SetForegroundWindow(window.hwnd)
    for _ in range(5):
        if safety.cancelled.is_set():raise RuntimeError(safety.reason)
        if capture.u.GetForegroundWindow()==window.hwnd:return window
        if safety.cancelled.wait(.1):raise RuntimeError(safety.reason)
    raise RuntimeError('無法自動切回遊戲；請手動切回遊戲後重新開始。')
