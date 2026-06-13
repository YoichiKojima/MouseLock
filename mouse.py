import ctypes
import time
# console
import threading
import time
import pyautogui


def mouse_monitor():
    while True:
        x, y = pyautogui.position()
        print(f"\rMouse Position: X={x}, Y={y}", end="", flush=True)
        time.sleep(0.05)


# Start background thread
thread = threading.Thread(target=mouse_monitor, daemon=True)
thread.start()
# end console

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

# Lock mouse to this area
# Example: first monitor 1920x1080
rect = RECT(0, 0, 1920, 1080)

ctypes.windll.user32.ClipCursor(ctypes.byref(rect))

try:
    print("Mouse locked. Press Ctrl+C to unlock.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    ctypes.windll.user32.ClipCursor(None)
    print("Mouse unlocked.")