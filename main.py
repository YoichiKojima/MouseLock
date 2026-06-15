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
gdi32 = ctypes.windll.gdi32

GWL_EXSTYLE = -20
GCLP_HCURSOR = -12
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
ULW_ALPHA = 0x00000002
BI_RGB = 0
DIB_RGB_COLORS = 0
AC_SRC_OVER = 0
AC_SRC_ALPHA = 0x01
DIM_ALPHA = 77
BORDER_DASH_ON = 3
BORDER_DASH_OFF = 1
WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
IDC_CROSS = 32515

WS_POPUP = 0x80000000
WS_EX_TOPMOST = 0x00000008
SW_SHOWNA = 8
ERROR_CLASS_ALREADY_EXISTS = 1410
OVERLAY_CLASS_NAME = "MoveMouseOverlay"
overlay_wndproc_ref = None
overlay_class_registered = False

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
    "screen_width": 0,
    "screen_height": 0,
    "dragging": False,
    "overlay_monitors": None,
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


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER)]


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
user32.UpdateLayeredWindow.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(POINT),
    ctypes.POINTER(SIZE),
    ctypes.c_void_p,
    ctypes.POINTER(POINT),
    ctypes.c_uint32,
    ctypes.POINTER(BLENDFUNCTION),
    ctypes.c_uint32,
]
user32.UpdateLayeredWindow.restype = ctypes.c_bool
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.CreateDIBSection.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(BITMAPINFO),
    ctypes.c_uint,
    ctypes.POINTER(ctypes.c_void_p),
    ctypes.c_void_p,
    ctypes.c_uint,
]
gdi32.CreateDIBSection.restype = ctypes.c_void_p
gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gdi32.SelectObject.restype = ctypes.c_void_p
gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
gdi32.DeleteObject.restype = ctypes.c_bool
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
gdi32.DeleteDC.restype = ctypes.c_bool
user32.EnumDisplayMonitors.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long,
]
user32.EnumDisplayMonitors.restype = ctypes.c_bool
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = ctypes.c_bool
user32.DefWindowProcW.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
user32.DefWindowProcW.restype = LRESULT
user32.CreateWindowExW.argtypes = [
    ctypes.c_ulong,
    ctypes.c_wchar_p,
    ctypes.c_wchar_p,
    ctypes.c_ulong,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
user32.CreateWindowExW.restype = ctypes.c_void_p
user32.DestroyWindow.argtypes = [ctypes.c_void_p]
user32.DestroyWindow.restype = ctypes.c_bool
user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.ShowWindow.restype = ctypes.c_bool
kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel32.GetModuleHandleW.restype = ctypes.c_void_p


WNDPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
    ]


user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = ctypes.c_uint16


cross_cursor = user32.LoadCursorW(None, IDC_CROSS)


def get_virtual_screen_bounds():
    left = user32.GetSystemMetrics(76)
    top = user32.GetSystemMetrics(77)
    width = user32.GetSystemMetrics(78)
    height = user32.GetSystemMetrics(79)
    return left, top, width, height


def enum_monitors():
    monitors = []

    @ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.POINTER(RECT),
        ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long,
    )
    def callback(hmon, _hdc, _lprect, _data):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            return 1
        rect = info.rcMonitor
        monitors.append(
            (
                rect.left,
                rect.top,
                rect.right - rect.left,
                rect.bottom - rect.top,
            )
        )
        return 1

    user32.EnumDisplayMonitors(None, None, callback, 0)
    if monitors:
        return monitors
    return [get_virtual_screen_bounds()]


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


def bind_cross_cursor(widget):
    def keep_cross_cursor(_event=None):
        user32.SetCursor(cross_cursor)

    widget.bind("<Enter>", keep_cross_cursor, add="+")
    widget.bind("<Motion>", keep_cross_cursor, add="+")


def dash_visible(pos):
    period = BORDER_DASH_ON + BORDER_DASH_OFF
    return (pos // period) % 2 == 0


def build_overlay_bitmap(width, height, cutout=None):
    pixel = bytes([0, 0, 0, DIM_ALPHA])
    buf = bytearray(pixel * (width * height))

    if cutout is None:
        return buf

    x1, y1, x2, y2 = cutout
    left = max(0, min(x1, x2))
    top = max(0, min(y1, y2))
    right = min(width, max(x1, x2))
    bottom = min(height, max(y1, y2))
    if right <= left or bottom <= top:
        return buf

    clear_row = bytes([0, 0, 0, 0]) * (right - left)
    row_bytes = width * 4
    for y in range(top, bottom):
        offset = y * row_bytes + left * 4
        buf[offset : offset + len(clear_row)] = clear_row

    white = bytes([255, 255, 255, 255])
    for x in range(left, right):
        if dash_visible(x - left):
            idx = (top * width + x) * 4
            buf[idx : idx + 4] = white
            if bottom - 1 > top:
                idx = ((bottom - 1) * width + x) * 4
                buf[idx : idx + 4] = white
    for y in range(top, bottom):
        if dash_visible(y - top):
            idx = (y * width + left) * 4
            buf[idx : idx + 4] = white
            if right - 1 > left:
                idx = (y * width + (right - 1)) * 4
                buf[idx : idx + 4] = white

    return buf


def monitor_cutout(overlay, cutout):
    if cutout is None:
        return None

    screen_left = selection["screen_left"]
    screen_top = selection["screen_top"]
    cx1, cy1, cx2, cy2 = cutout
    gx1 = cx1 + screen_left
    gy1 = cy1 + screen_top
    gx2 = cx2 + screen_left
    gy2 = cy2 + screen_top

    mon_left = overlay["left"]
    mon_top = overlay["top"]
    mon_right = mon_left + overlay["width"]
    mon_bottom = mon_top + overlay["height"]

    left = max(min(gx1, gx2), mon_left)
    top = max(min(gy1, gy2), mon_top)
    right = min(max(gx1, gx2), mon_right)
    bottom = min(max(gy1, gy2), mon_bottom)
    if right <= left or bottom <= top:
        return None

    return (left - mon_left, top - mon_top, right - mon_left, bottom - mon_top)


def place_overlay_window(hwnd, left, top, width, height):
    user32.SetWindowPos(
        hwnd,
        HWND_TOPMOST,
        int(left),
        int(top),
        int(width),
        int(height),
        SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


def update_one_layered_overlay(overlay, cutout=None):
    hwnd = overlay["hwnd"]
    width = overlay["width"]
    height = overlay["height"]
    buf = build_overlay_bitmap(width, height, cutout)

    hdc_screen = user32.GetDC(None)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB

    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(
        hdc_mem,
        ctypes.byref(bmi),
        DIB_RGB_COLORS,
        ctypes.byref(bits),
        None,
        0,
    )
    if not hbmp or not bits.value:
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(None, hdc_screen)
        return

    src = (ctypes.c_char * len(buf)).from_buffer(buf)
    ctypes.memmove(bits.value, src, len(buf))

    old_obj = gdi32.SelectObject(hdc_mem, hbmp)
    blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
    user32.UpdateLayeredWindow(
        hwnd,
        hdc_screen,
        ctypes.byref(POINT(overlay["left"], overlay["top"])),
        ctypes.byref(SIZE(width, height)),
        hdc_mem,
        ctypes.byref(POINT(0, 0)),
        0,
        ctypes.byref(blend),
        ULW_ALPHA,
    )

    gdi32.SelectObject(hdc_mem, old_obj)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(None, hdc_screen)


def update_layered_overlay(cutout=None):
    for overlay in selection.get("overlay_monitors") or []:
        local_cutout = monitor_cutout(overlay, cutout)
        update_one_layered_overlay(overlay, local_cutout)


def destroy_selection_overlay():
    global overlay_windows
    for overlay in selection.get("overlay_monitors") or []:
        user32.DestroyWindow(overlay["hwnd"])
    selection["overlay_monitors"] = None
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


def ensure_overlay_window_class():
    global overlay_wndproc_ref, overlay_class_registered
    if overlay_class_registered:
        return True

    @WNDPROC
    def overlay_wndproc(hwnd, msg, wparam, lparam):
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    overlay_wndproc_ref = overlay_wndproc
    wc = WNDCLASSW()
    wc.lpfnWndProc = overlay_wndproc_ref
    wc.hInstance = kernel32.GetModuleHandleW(None)
    wc.hCursor = cross_cursor
    wc.lpszClassName = OVERLAY_CLASS_NAME

    atom = user32.RegisterClassW(ctypes.byref(wc))
    if not atom and ctypes.get_last_error() != ERROR_CLASS_ALREADY_EXISTS:
        print(f"RegisterClassW failed, error={ctypes.get_last_error()}")
        return False

    overlay_class_registered = True
    return True


def create_monitor_overlay(mon_left, mon_top, mon_width, mon_height):
    if not ensure_overlay_window_class():
        return None

    hwnd = user32.CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
        OVERLAY_CLASS_NAME,
        None,
        WS_POPUP,
        int(mon_left),
        int(mon_top),
        int(mon_width),
        int(mon_height),
        None,
        None,
        kernel32.GetModuleHandleW(None),
        None,
    )
    if not hwnd:
        print(f"CreateWindowExW failed, error={ctypes.get_last_error()}")
        return None

    user32.ShowWindow(hwnd, SW_SHOWNA)
    place_overlay_window(hwnd, mon_left, mon_top, mon_width, mon_height)

    return {
        "hwnd": hwnd,
        "left": mon_left,
        "top": mon_top,
        "width": mon_width,
        "height": mon_height,
    }


def create_selection_overlay(left, top, width, height):
    global overlay_windows

    selection["screen_left"] = left
    selection["screen_top"] = top
    selection["screen_width"] = width
    selection["screen_height"] = height

    overlays = []
    for mon_left, mon_top, mon_width, mon_height in enum_monitors():
        overlay = create_monitor_overlay(mon_left, mon_top, mon_width, mon_height)
        if overlay is not None:
            overlays.append(overlay)

    selection["overlay_monitors"] = overlays

    for overlay in overlays:
        update_one_layered_overlay(overlay)

    overlay_windows = [overlay["hwnd"] for overlay in overlays]
    return overlays


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

    state = {"start_x": None, "start_y": None}
    selection["state"] = state

    def to_canvas_coords(x, y):
        return x - selection["screen_left"], y - selection["screen_top"]

    def on_press(x, y):
        state["start_x"] = x
        state["start_y"] = y
        selection["dragging"] = True
        update_layered_overlay()

    def on_drag(x, y):
        if state["start_x"] is None:
            return
        cx1, cy1 = to_canvas_coords(state["start_x"], state["start_y"])
        cx2, cy2 = to_canvas_coords(x, y)
        update_layered_overlay((cx1, cy1, cx2, cy2))

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
