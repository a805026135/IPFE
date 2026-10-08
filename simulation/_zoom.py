"""Ctrl+wheel zoom-out on the Qtenv canvas, then capture-ready."""
import ctypes
import ctypes.wintypes as wt
import sys
import time

user32 = ctypes.windll.user32
keyword, rx, ry, notches = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])

results = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
def cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        n = user32.GetWindowTextLengthW(hwnd)
        if n > 0:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if keyword.lower() in buf.value.lower():
                results.append((hwnd, buf.value))
    return True


user32.EnumWindows(cb, 0)
results.sort(key=lambda t: -len(t[1]))
hwnd, title = results[0]
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(1)
rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
x, y = rect.left + rx, rect.top + ry
user32.SetCursorPos(x, y)
time.sleep(0.5)
user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
for _ in range(notches):
    user32.mouse_event(0x0800, 0, 0, -120, 0)  # WHEEL down = zoom out
    time.sleep(0.03)
user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
print("zoomed out x", notches)
