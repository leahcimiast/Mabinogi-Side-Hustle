"""Automatic game validation used by the single-window dashboard."""
from . import capture

def prepare_game(safety):
    windows=capture.detect()
    if len(windows)!=1:
        raise RuntimeError(f'找到 {len(windows)} 個遊戲視窗；請只保留一個瑪奇 Mobile 視窗。')
    window=windows[0]
    capture.capture(window)  # Automatically verify foreground, size and usable content.
    safety.arm(window)
    safety.check(window)
    return window
