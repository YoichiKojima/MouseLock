import ctypes
import keyboard
import tkinter as tk

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32

overlay_windows = []
mouse_clip = {"rect": None, "job": None}
root = tk.Tk()
root.withdraw()


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


user32.ClipCursor.argtypes = [ctypes.POINTER(RECT)]
user32.ClipCursor.restype = ctypes.c_bool


def get_virtual_screen_bounds():
    left = user32.GetSystemMetrics(76)
    top = user32.GetSystemMetrics(77)
    width = user32.GetSystemMetrics(78)
    height = user32.GetSystemMetrics(79)
    return left, top, width, height


def close_overlay(_event=None):
    global overlay_windows
    for window in overlay_windows:
        window.destroy()
    overlay_windows = []


def apply_clip():
    rect_data = mouse_clip["rect"]
    if rect_data is None:
        return False

    x, y, width, height = rect_data
    rect = RECT(x, y, x + width, y + height)
    ok = user32.ClipCursor(ctypes.byref(rect))
    if not ok:
        print(f"ClipCursor failed, error={ctypes.get_last_error()}")
    return ok


def release_clip():
    user32.ClipCursor.argtypes = [ctypes.c_void_p]
    user32.ClipCursor(None)
    user32.ClipCursor.argtypes = [ctypes.POINTER(RECT)]


def maintain_clip():
    if mouse_clip["rect"] is None:
        mouse_clip["job"] = None
        return

    apply_clip()
    mouse_clip["job"] = root.after(100, maintain_clip)


def lock_mouse_to_area(x, y, width, height):
    mouse_clip["rect"] = (x, y, width, height)
    apply_clip()

    if mouse_clip["job"] is not None:
        root.after_cancel(mouse_clip["job"])
    maintain_clip()
    print(f"Mouse locked to x={x}, y={y}, width={width}, height={height}")


def unlock_mouse():
    mouse_clip["rect"] = None
    if mouse_clip["job"] is not None:
        root.after_cancel(mouse_clip["job"])
        mouse_clip["job"] = None
    release_clip()
    print("Mouse unlocked.")


def start_area_selection():
    global overlay_windows
    left, top, width, height = get_virtual_screen_bounds()

    window = tk.Toplevel(root)
    window.geometry(f"{width}x{height}+{left}+{top}")
    window.attributes("-topmost", True)
    window.attributes("-alpha", 0.3)
    window.configure(bg="black")
    window.overrideredirect(True)

    canvas = tk.Canvas(window, highlightthickness=0, bg="black", cursor="cross")
    canvas.pack(fill=tk.BOTH, expand=True)

    state = {"start_x": None, "start_y": None, "rect": None}

    def to_canvas_coords(x, y):
        return x - left, y - top

    def on_press(event):
        state["start_x"] = event.x_root
        state["start_y"] = event.y_root
        if state["rect"] is not None:
            canvas.delete(state["rect"])
            state["rect"] = None

    def on_drag(event):
        if state["start_x"] is None:
            return
        if state["rect"] is not None:
            canvas.delete(state["rect"])
        cx1, cy1 = to_canvas_coords(state["start_x"], state["start_y"])
        cx2, cy2 = to_canvas_coords(event.x_root, event.y_root)
        state["rect"] = canvas.create_rectangle(
            cx1, cy1, cx2, cy2, outline="red", width=2
        )

    def on_release(event):
        if state["start_x"] is None:
            return

        x1, y1 = state["start_x"], state["start_y"]
        x2, y2 = event.x_root, event.y_root
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)

        close_overlay()

        if w > 0 and h > 0:
            print(f"x={x}, y={y}, width={w}, height={h}")

            def apply_lock():
                lock_mouse_to_area(x, y, w, h)

            root.after(50, apply_lock)

    window.bind("<Escape>", close_overlay)
    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)

    overlay_windows.append(window)


def my_function():
    def toggle_selection():
        if overlay_windows:
            close_overlay()
            return
        start_area_selection()

    root.after(0, toggle_selection)


def clear_selection():
    root.after(0, unlock_mouse)


keyboard.add_hotkey("alt+c", my_function)
keyboard.add_hotkey("alt+x", clear_selection)

try:
    root.mainloop()
except KeyboardInterrupt:
    unlock_mouse()
    print("Stopped.")
