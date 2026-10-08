"""Maximize the Qtenv window and zoom in/out N notches (while it holds focus).
Usage: _maxzoom.py <keyword> <notches> <in|out>
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

user32 = ctypes.windll.user32
keyword, notches, direction = sys.argv[1], int(sys.argv[2]), sys.argv[3]

res = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
def cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        n = user32.GetWindowTextLengthW(hwnd)
        if n > 0:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if keyword.lower() in buf.value.lower():
                res.append(hwnd)
    return True


user32.EnumWindows(cb, 0)
if not res:
    print("NO WINDOW")
    sys.exit(1)
hwnd = res[0]
user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
time.sleep(2)
vk = 0xBB if direction == "in" else 0xBD  # plus / minus
user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
for _ in range(notches):
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, 2, 0)
    time.sleep(0.08)
user32.keybd_event(0x11, 0, 2, 0)
time.sleep(0.5)
print("maximized + zoomed", direction, "x", notches)
