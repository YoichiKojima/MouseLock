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


def lock_mouse_to_area(x, y, width, height):
    rect = RECT(x, y, x + width, y + height)
    user32.ClipCursor(ctypes.byref(rect))
    print(f"Mouse locked to x={x}, y={y}, width={width}, height={height}")


def unlock_mouse():
    user32.ClipCursor(None)
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

        if w > 0 and h > 0:
            print(f"x={x}, y={y}, width={w}, height={h}")
            lock_mouse_to_area(x, y, w, h)

        close_overlay()

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
    unlock_mouse()


keyboard.add_hotkey("alt+c", my_function)
keyboard.add_hotkey("alt+x", clear_selection)

try:
    root.mainloop()
except KeyboardInterrupt:
    unlock_mouse()
    print("Stopped.")
