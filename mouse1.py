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
kernel32 = ctypes.windll.kernel32

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

overlay_windows = []
mouse_clip = {"rect": None, "job": None}
saved_lock_rect = {"rect": None}
selection_session = {"restore_on_cancel": False}
selection = {"foreground_hwnd": None, "screen_left": 0, "screen_top": 0}

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


def set_overlay_style(hwnd):
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(
        hwnd,
        GWL_EXSTYLE,
        style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
    )


def restore_foreground(hwnd):
    if not hwnd or not user32.IsWindow(hwnd):
        return

    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)

    target_thread = user32.GetWindowThreadProcessId(hwnd, None)
    current_thread = kernel32.GetCurrentThreadId()
    attached = False
    if target_thread != current_thread:
        attached = bool(user32.AttachThreadInput(current_thread, target_thread, True))

    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)

    if attached:
        user32.AttachThreadInput(current_thread, target_thread, False)


def close_overlay(restore_focus=True):
    global overlay_windows
    foreground = selection["foreground_hwnd"] if restore_focus else None

    for window in overlay_windows:
        window.destroy()
    overlay_windows = []

    if foreground:
        root.after(50, lambda: restore_foreground(foreground))


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
    rect = (x, y, width, height)
    mouse_clip["rect"] = rect
    saved_lock_rect["rect"] = rect
    apply_clip()

    if mouse_clip["job"] is not None:
        root.after_cancel(mouse_clip["job"])
    maintain_clip()
    print(f"Mouse locked to x={x}, y={y}, width={width}, height={height}")


def unlock_mouse(quiet=False):
    mouse_clip["rect"] = None
    if mouse_clip["job"] is not None:
        root.after_cancel(mouse_clip["job"])
        mouse_clip["job"] = None
    release_clip()
    if not quiet:
        print("Mouse unlocked.")


def restore_saved_lock():
    if saved_lock_rect["rect"] is None:
        return
    x, y, width, height = saved_lock_rect["rect"]
    lock_mouse_to_area(x, y, width, height)


def end_selection_session(restore_original=False):
    should_restore = restore_original and selection_session["restore_on_cancel"]
    selection_session["restore_on_cancel"] = False
    had_overlay = bool(overlay_windows)
    close_overlay(restore_focus=True)
    if should_restore and had_overlay and saved_lock_rect["rect"] is not None:
        root.after(50, restore_saved_lock)


def start_area_selection():
    global overlay_windows

    if overlay_windows:
        end_selection_session(restore_original=True)
        return

    selection_session["restore_on_cancel"] = saved_lock_rect["rect"] is not None

    if mouse_clip["rect"] is not None:
        unlock_mouse(quiet=True)

    selection["foreground_hwnd"] = user32.GetForegroundWindow()
    left, top, width, height = get_virtual_screen_bounds()
    selection["screen_left"] = left
    selection["screen_top"] = top

    window = tk.Toplevel(root)
    window.geometry(f"{width}x{height}+{left}+{top}")
    window.attributes("-topmost", True)
    window.attributes("-alpha", 0.3)
    window.configure(bg="black")
    window.overrideredirect(True)
    window.update_idletasks()
    set_overlay_style(window.winfo_id())

    canvas = tk.Canvas(window, highlightthickness=0, bg="black", cursor="cross")
    canvas.pack(fill=tk.BOTH, expand=True)

    state = {"start_x": None, "start_y": None, "rect": None}

    def to_canvas_coords(x, y):
        return x - selection["screen_left"], y - selection["screen_top"]

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
        foreground = selection["foreground_hwnd"]
        should_restore = selection_session["restore_on_cancel"]
        selection_session["restore_on_cancel"] = False

        close_overlay(restore_focus=False)

        if w > 0 and h > 0:
            print(f"x={x}, y={y}, width={w}, height={h}")

            def apply_lock():
                lock_mouse_to_area(x, y, w, h)
                if foreground:
                    restore_foreground(foreground)

            root.after(50, apply_lock)
        elif should_restore and saved_lock_rect["rect"] is not None:

            def restore():
                restore_saved_lock()
                if foreground:
                    restore_foreground(foreground)

            root.after(50, restore)
        elif foreground:
            root.after(50, lambda: restore_foreground(foreground))

    def on_escape(_event=None):
        end_selection_session(restore_original=True)

    window.bind("<Escape>", on_escape)
    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)

    overlay_windows.append(window)


def my_function():
    root.after(0, start_area_selection)


def toggle_lock():
    def do_toggle():
        if mouse_clip["rect"] is not None:
            unlock_mouse()
            print("Mouse unlocked. Press Alt+X again to lock to the original area.")
        elif saved_lock_rect["rect"] is not None:
            x, y, width, height = saved_lock_rect["rect"]
            lock_mouse_to_area(x, y, width, height)
        else:
            print("No lock area. Press Alt+C to select an area first.")

    root.after(0, do_toggle)


def cancel_selection():
    if overlay_windows:
        root.after(0, lambda: end_selection_session(restore_original=True))


keyboard.add_hotkey("alt+c", my_function)
keyboard.add_hotkey("alt+x", toggle_lock)
keyboard.add_hotkey("esc", cancel_selection)

try:
    root.mainloop()
except KeyboardInterrupt:
    close_overlay(restore_focus=False)
    unlock_mouse()
    print("Stopped.")
