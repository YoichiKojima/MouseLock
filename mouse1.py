import ctypes
import keyboard
import tkinter as tk

user32 = ctypes.windll.user32

overlay_windows = []
root = tk.Tk()
root.withdraw()


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def get_monitor_bounds():
    monitors = []

    def callback(_hMonitor, _hdcMonitor, lprcMonitor, _dwData):
        rect = lprcMonitor.contents
        monitors.append(
            (
                rect.left,
                rect.top,
                rect.right - rect.left,
                rect.bottom - rect.top,
            )
        )
        return True

    enum_proc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.POINTER(RECT),
        ctypes.c_double,
    )(callback)
    user32.EnumDisplayMonitors(None, None, enum_proc, 0)
    return monitors


def close_overlay(_event=None):
    global overlay_windows
    for window in overlay_windows:
        window.destroy()
    overlay_windows = []


def my_function():
    def toggle_overlay():
        global overlay_windows
        if overlay_windows:
            close_overlay()
            return

        for x, y, width, height in get_monitor_bounds():
            window = tk.Toplevel(root)
            window.geometry(f"{width}x{height}+{x}+{y}")
            window.attributes("-topmost", True)
            window.attributes("-alpha", 0.3)
            window.configure(bg="black")
            window.overrideredirect(True)
            window.bind("<Escape>", close_overlay)
            window.bind("<Button-1>", close_overlay)
            overlay_windows.append(window)

    root.after(0, toggle_overlay)


keyboard.add_hotkey("alt+c", my_function)

try:
    root.mainloop()
except KeyboardInterrupt:
    print("Stopped.")
