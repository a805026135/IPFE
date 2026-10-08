"""Capture a screenshot of the topmost window whose title contains a keyword."""
import ctypes
import ctypes.wintypes as wt
import sys

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

out_path, keyword = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "SUMO")

results = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
def cb(hwnd, lparam):
    if not user32.IsWindowVisible(hwnd):
        return True
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return True
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    if keyword.lower() in buf.value.lower():
        results.append((hwnd, buf.value))
    return True


user32.EnumWindows(cb, 0)
if not results:
    print("NO WINDOW MATCHING", keyword)
    sys.exit(1)
results.sort(key=lambda t: -len(t[1]))
hwnd, title = results[0]
print("capturing:", title)

# bring to front and restore if minimized
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
import time
time.sleep(2)

rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
w, h = rect.right - rect.left, rect.bottom - rect.top
print("rect", rect.left, rect.top, w, h)

hdc = user32.GetDC(hwnd)
mem = gdi32.CreateCompatibleDC(hdc)
bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(mem, bmp)
gdi32.BitBlt(mem, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)

import struct


class BMPINFOHEADER:
    def __init__(self, w, h):
        self.data = struct.pack("<IiiHHIIiiII", 40, w, -h, 1, 32, 0, w * h * 4, 0, 0, 0, 0)


info = BMPINFOHEADER(w, h).data
buf = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(mem, bmp, 0, h, buf, info, 0)

# write BMP (32bpp, bottom-up flip handled by negative height)
bmp_header = struct.pack("<2sIHHI" + "IiiHHIIiiII", b"BM", 14 + 40 + w * h * 4, 0, 0, 14 + 40, 40, w, -h, 1, 32, 0, w * h * 4, 0, 0, 0, 0)
with open(out_path, "wb") as f:
    f.write(bmp_header)
    f.write(buf.raw)

gdi32.DeleteObject(bmp)
gdi32.DeleteDC(mem)
user32.ReleaseDC(hwnd, hdc)
print("saved", out_path)
