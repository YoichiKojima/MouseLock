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
GCLP_HCURSOR = -12
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
IDC_CROSS = 32515

cross_cursor = user32.LoadCursorW(None, IDC_CROSS)

overlay_windows = []
mouse_hook = {"handle": None, "proc": None}
mouse_events = []
hook_active = ctypes.c_int(0)
hook_dragging = ctypes.c_int(0)
mouse_clip = {"rect": None, "job": None}
saved_lock_rect = {"rect": None}
selection_session = {"restore_on_cancel": False}
selection = {
    "active": False,
    "foreground_hwnd": None,
    "screen_left": 0,
    "screen_top": 0,
    "dragging": False,
    "window": None,
    "canvas": None,
    "state": None,
    "on_press": None,
    "on_drag": None,
    "on_release": None,
    "poll_job": None,
}
session_state = {"locked": False}

root = tk.Tk()
root.withdraw()


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_ulong),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("pt", POINT),
        ("mouseData", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


if ctypes.sizeof(ctypes.c_void_p) == 8:
    LRESULT = ctypes.c_longlong
else:
    LRESULT = ctypes.c_long

HOOKPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    ctypes.c_int,
    ctypes.c_uint,
    ctypes.c_void_p,
)


user32.ClipCursor.argtypes = [ctypes.POINTER(RECT)]
user32.ClipCursor.restype = ctypes.c_bool
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    HOOKPROC,
    ctypes.c_void_p,
    ctypes.c_uint,
]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_uint,
    ctypes.c_void_p,
]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.UnhookWindowsHookEx.restype = ctypes.c_bool


def get_virtual_screen_bounds():
    left = user32.GetSystemMetrics(76)
    top = user32.GetSystemMetrics(77)
    width = user32.GetSystemMetrics(78)
    height = user32.GetSystemMetrics(79)
    return left, top, width, height


def get_monitor_bounds_at(x, y):
    point = POINT(x, y)
    monitor = user32.MonitorFromPoint(point, 2)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(monitor, ctypes.byref(info))
    rect = info.rcMonitor
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def get_cursor_pos():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def is_workstation_locked():
    desktop = user32.OpenInputDesktop(0, False, 0)
    if desktop:
        user32.CloseDesktop(desktop)
        return False
    return True


def on_session_unlock():
    keyboard.stash_state()
    if mouse_clip["rect"] is not None:
        apply_clip()


def poll_session_state():
    locked = is_workstation_locked()
    if session_state["locked"] and not locked:
        on_session_unlock()
    session_state["locked"] = locked
    root.after(500, poll_session_state)


def set_overlay_style(hwnd):
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(
        hwnd,
        GWL_EXSTYLE,
        style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
    )


def set_overlay_cursor(hwnd):
    if hasattr(user32, "SetClassLongPtrW"):
        user32.SetClassLongPtrW(hwnd, GCLP_HCURSOR, cross_cursor)
    else:
        user32.SetClassLongW(hwnd, GCLP_HCURSOR, cross_cursor)


def show_overlay_without_focus(window, left, top, width, height):
    window.deiconify()
    window.attributes("-topmost", True)
    window.configure(cursor="crosshair")
    window.update_idletasks()
    hwnd = window.winfo_id()
    set_overlay_style(hwnd)
    set_overlay_cursor(hwnd)
    user32.SetCursor(cross_cursor)
    user32.SetWindowPos(
        hwnd,
        HWND_TOPMOST,
        left,
        top,
        width,
        height,
        SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


def stop_mouse_pump():
    job = selection.get("poll_job")
    if job is not None:
        root.after_cancel(job)
    selection["poll_job"] = None
    mouse_events.clear()


def pump_mouse_events():
    if not selection.get("active"):
        selection["poll_job"] = None
        return

    while mouse_events:
        w_param, x, y = mouse_events.pop(0)
        if w_param == WM_LBUTTONDOWN:
            selection["dragging"] = True
            selection["on_press"](x, y)
        elif w_param == WM_LBUTTONUP:
            hook_dragging.value = 0
            selection["on_release"](x, y)

    if selection.get("dragging"):
        x, y = get_cursor_pos()
        selection["on_drag"](x, y)

    selection["poll_job"] = root.after(8, pump_mouse_events)


def start_mouse_pump():
    stop_mouse_pump()
    selection["poll_job"] = root.after(8, pump_mouse_events)


def install_mouse_hook():
    if mouse_hook["handle"] is not None:
        return

    @HOOKPROC
    def hook_proc(n_code, w_param, l_param):
        handle = mouse_hook["handle"]
        if n_code >= 0 and hook_active.value:
            mouse = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            x, y = mouse.pt.x, mouse.pt.y
            if w_param == WM_LBUTTONDOWN:
                mouse_events.append((w_param, x, y))
                hook_dragging.value = 1
                return 1
            if w_param == WM_LBUTTONUP:
                mouse_events.append((w_param, x, y))
                return 1
        if handle:
            return user32.CallNextHookEx(handle, n_code, w_param, l_param)
        return 0

    mouse_hook["proc"] = hook_proc
    handle = user32.SetWindowsHookExW(WH_MOUSE_LL, hook_proc, None, 0)
    if not handle:
        print(f"Mouse hook failed, error={ctypes.get_last_error()}")
        mouse_hook["proc"] = None
        return
    mouse_hook["handle"] = handle


def uninstall_mouse_hook():
    handle = mouse_hook["handle"]
    if handle:
        user32.UnhookWindowsHookEx(handle)
    mouse_hook["handle"] = None
    mouse_hook["proc"] = None


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


def destroy_selection_overlay():
    global overlay_windows
    window = selection["window"]
    if window is not None:
        window.destroy()
    selection["window"] = None
    selection["canvas"] = None
    overlay_windows = []


def end_selection_mode(restore_focus=True):
    foreground = selection["foreground_hwnd"] if restore_focus else None

    hook_active.value = 0
    hook_dragging.value = 0
    selection["active"] = False
    selection["dragging"] = False
    selection["state"] = None
    selection["on_press"] = None
    selection["on_drag"] = None
    selection["on_release"] = None
    stop_mouse_pump()
    uninstall_mouse_hook()
    destroy_selection_overlay()

    if foreground:
        root.after(50, lambda: restore_foreground(foreground))


def close_overlay(restore_focus=True):
    end_selection_mode(restore_focus=restore_focus)


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
    was_active = selection["active"]
    end_selection_mode(restore_focus=True)
    if should_restore and was_active and saved_lock_rect["rect"] is not None:
        root.after(50, restore_saved_lock)


def create_selection_overlay(left, top, width, height):
    selection["screen_left"] = left
    selection["screen_top"] = top

    window = tk.Toplevel(root)
    window.withdraw()
    window.geometry(f"{width}x{height}+{left}+{top}")
    window.attributes("-alpha", 0.3)
    window.configure(bg="black", cursor="crosshair")
    window.overrideredirect(True)

    canvas = tk.Canvas(window, highlightthickness=0, bg="black", cursor="crosshair")
    canvas.pack(fill=tk.BOTH, expand=True)

    def keep_cross_cursor(_event=None):
        user32.SetCursor(cross_cursor)

    for widget in (window, canvas):
        widget.bind("<Enter>", keep_cross_cursor, add="+")
        widget.bind("<Motion>", keep_cross_cursor, add="+")

    window.update_idletasks()
    show_overlay_without_focus(window, left, top, width, height)

    selection["window"] = window
    selection["canvas"] = canvas
    overlay_windows.append(window)
    return canvas


def start_area_selection():
    global overlay_windows

    if selection["active"]:
        end_selection_session(restore_original=True)
        return

    selection_session["restore_on_cancel"] = saved_lock_rect["rect"] is not None

    if mouse_clip["rect"] is not None:
        unlock_mouse(quiet=True)

    selection["foreground_hwnd"] = user32.GetForegroundWindow()
    left, top, width, height = get_virtual_screen_bounds()
    selection["active"] = True
    selection["dragging"] = False

    state = {"start_x": None, "start_y": None, "rect": None}
    selection["state"] = state

    def to_canvas_coords(x, y):
        return x - selection["screen_left"], y - selection["screen_top"]

    def on_press(x, y):
        canvas = selection["canvas"]
        state["start_x"] = x
        state["start_y"] = y
        selection["dragging"] = True
        if state["rect"] is not None:
            canvas.delete(state["rect"])
            state["rect"] = None

    def on_drag(x, y):
        canvas = selection["canvas"]
        if state["start_x"] is None:
            return
        if state["rect"] is not None:
            canvas.delete(state["rect"])
        cx1, cy1 = to_canvas_coords(state["start_x"], state["start_y"])
        cx2, cy2 = to_canvas_coords(x, y)
        state["rect"] = canvas.create_rectangle(
            cx1, cy1, cx2, cy2, outline="red", width=2
        )
        canvas.update_idletasks()

    def on_release(x, y):
        if state["start_x"] is None:
            selection["dragging"] = False
            return

        selection["dragging"] = False

        x1, y1 = state["start_x"], state["start_y"]
        x2, y2 = x, y
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        foreground = selection["foreground_hwnd"]
        selection_session["restore_on_cancel"] = False

        end_selection_mode(restore_focus=False)

        if w == 0 and h == 0:
            x, y, w, h = get_monitor_bounds_at(x1, y1)

        print(f"x={x}, y={y}, width={w}, height={h}")

        def apply_lock():
            lock_mouse_to_area(x, y, w, h)
            if foreground:
                restore_foreground(foreground)

        root.after(50, apply_lock)

    selection["on_press"] = on_press
    selection["on_drag"] = on_drag
    selection["on_release"] = on_release

    install_mouse_hook()
    if not mouse_hook["handle"]:
        selection["active"] = False
        selection["state"] = None
        selection["on_press"] = None
        selection["on_drag"] = None
        selection["on_release"] = None
        return
    hook_active.value = 1
    hook_dragging.value = 0
    mouse_events.clear()
    create_selection_overlay(left, top, width, height)
    start_mouse_pump()
    restore_foreground(selection["foreground_hwnd"])
    print("Click and drag to select an area. Press Esc to cancel.")


def my_function():
    root.after(0, start_area_selection)


def toggle_lock():
    def do_toggle():
        if selection["active"]:
            return
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
    if selection["active"]:
        root.after(0, lambda: end_selection_session(restore_original=True))


keyboard.add_hotkey("alt+c", my_function)
keyboard.add_hotkey("alt+x", toggle_lock)
keyboard.add_hotkey("esc", cancel_selection)

session_state["locked"] = is_workstation_locked()
root.after(500, poll_session_state)

try:
    root.mainloop()
except KeyboardInterrupt:
    hook_active.value = 0
    hook_dragging.value = 0
    stop_mouse_pump()
    close_overlay(restore_focus=False)
    uninstall_mouse_hook()
    unlock_mouse()
    print("Stopped.")
