"""Click at (rx, ry) relative to the topmost window matching keyword."""
import ctypes
import ctypes.wintypes as wt
import sys
import time

user32 = ctypes.windll.user32
keyword, rx, ry = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

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
if not results:
    print("NO WINDOW")
    sys.exit(1)
results.sort(key=lambda t: -len(t[1]))
hwnd, title = results[0]
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(1)

rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
x = rect.left + rx
y = rect.top + ry
user32.SetCursorPos(x, y)
time.sleep(0.4)
user32.mouse_event(2, 0, 0, 0, 0)   # LEFTDOWN
user32.mouse_event(4, 0, 0, 0, 0)   # LEFTUP
time.sleep(0.5)
print("clicked", x, y, "in", title)
