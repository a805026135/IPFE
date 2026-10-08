"""Bring the window matching keyword to foreground and press given keys."""
import ctypes
import ctypes.wintypes as wt
import sys
import time

user32 = ctypes.windll.user32
out_path_unused, keyword, keys = None, sys.argv[1], sys.argv[2]

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
    print("NO WINDOW", keyword)
    sys.exit(1)
results.sort(key=lambda t: -len(t[1]))
hwnd, title = results[0]
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(1.5)
print("focused:", title)

VK = {"F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77}
for k in keys.split(","):
    vk = VK.get(k)
    if not vk:
        continue
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, 2, 0)  # KEYUP
    time.sleep(0.5)
print("keys sent:", keys)
