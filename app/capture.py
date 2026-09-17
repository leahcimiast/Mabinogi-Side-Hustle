"""Foreground desktop capture of the Win32 client rectangle, never the outer window."""
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageGrab, ImageChops

BASELINE = (1280, 960)
u = C.WinDLL('user32', use_last_error=True)
k = C.WinDLL('kernel32', use_last_error=True)
u.GetForegroundWindow.restype = W.HWND
u.GetAncestor.argtypes = [W.HWND, W.UINT]
u.GetAncestor.restype = W.HWND
u.IsWindowVisible.argtypes = [W.HWND]
u.IsIconic.argtypes = [W.HWND]
u.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
u.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]
u.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
u.GetWindowTextLengthW.argtypes = [W.HWND]
u.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
k.OpenProcess.restype = W.HANDLE
k.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)]
k.CloseHandle.argtypes = [W.HANDLE]


def dpi_aware():
    # Must run before Tk creates any windows.
    try:
        u.SetProcessDpiAwarenessContext(C.c_void_p(-4))
    except AttributeError:
        u.SetProcessDPIAware()


@dataclass(frozen=True)
class GameWindow:
    hwnd: int
    title: str
    process: str
    rect: tuple


def client_rect(hwnd):
    r, p = W.RECT(), W.POINT()
    if not u.GetClientRect(hwnd, C.byref(r)) or not u.ClientToScreen(hwnd, C.byref(p)):
        raise RuntimeError("Cannot read game client rectangle")
    return p.x, p.y, p.x + r.right, p.y + r.bottom


def process_name(hwnd):
    pid = W.DWORD()
    u.GetWindowThreadProcessId(hwnd, C.byref(pid))
    handle = k.OpenProcess(0x1000, False, pid.value)
    if not handle:
        return ''
    try:
        name, size = C.create_unicode_buffer(32768), W.DWORD(32768)
        if k.QueryFullProcessImageNameW(handle, 0, name, C.byref(size)):
            return Path(name.value).name
        return ''
    finally:
        k.CloseHandle(handle)


def detect():
    found = []
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def visit(hwnd, _):
        if u.IsWindowVisible(hwnd):
            title = C.create_unicode_buffer(u.GetWindowTextLengthW(hwnd) + 1)
            u.GetWindowTextW(hwnd, title, len(title))
            proc = process_name(hwnd)
            # Titles are descriptive only: the helper itself includes the game title.
            # An unreadable or different process must never become an input target.
            if proc.lower() == 'mabinogimobile.exe':
                found.append(GameWindow(hwnd, title.value, proc, client_rect(hwnd)))
        return True
    callback = callback_type(visit)
    u.EnumWindows(callback, 0)
    return found


def capture(window):
    if process_name(window.hwnd).lower() != 'mabinogimobile.exe':
        raise RuntimeError("Game process identity could not be verified")
    if u.GetForegroundWindow() != window.hwnd or u.IsIconic(window.hwnd):
        raise RuntimeError("請將遊戲切至前景；只擷取未最小化的遊戲")
    rect = client_rect(window.hwnd)
    if (rect[2]-rect[0], rect[3]-rect[1]) != BASELINE:
        raise RuntimeError(f"遊戲 client area 必須為 1280 × 960，目前為 {rect[2]-rect[0]} × {rect[3]-rect[1]}")
    vx,vy = u.GetSystemMetrics(76),u.GetSystemMetrics(77)
    if rect[0] < vx or rect[1] < vy or rect[2] > vx+u.GetSystemMetrics(78) or rect[3] > vy+u.GetSystemMetrics(79):
        raise RuntimeError('Game client is partly outside the desktop')
    image = ImageGrab.grab(bbox=rect, all_screens=True)
    if u.GetForegroundWindow() != window.hwnd or client_rect(window.hwnd) != rect:
        raise RuntimeError("Capture invalidated by focus or window movement")
    if max(high-low for low, high in image.convert('RGB').getextrema()) < 8:
        raise RuntimeError("Blank/protected capture; no usable game image")
    return image


def reference(path):
    with Image.open(path) as source:
        image = source.convert('RGB')
    # Only auto-crop an exact baseline surrounded by near-black recording canvas.
    if image.size == (1920, 1080):
        mask = ImageChops.difference(image, Image.new('RGB', image.size)).convert('L').point(lambda x: 255 if x > 18 else 0)
        bounds = mask.getbbox()
        if bounds and bounds[0] < 80 and bounds[1] < 80 and 1200 <= bounds[2] <= 1280 and 900 <= bounds[3] <= 960:
            return image.crop((0, 0, 1280, 960)), 'Recording top-left crop (0, 0, 1280, 960); reference only'
        raise ValueError("Recording canvas does not contain an unambiguous 1280 × 960 rectangle")
    return image, f"Reference {image.width} × {image.height}; not live setup validation"
