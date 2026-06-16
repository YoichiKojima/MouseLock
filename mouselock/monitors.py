import ctypes

from mouselock.win32 import MONITORINFO, POINT, RECT, user32


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


def restore_foreground(hwnd):
    from mouselock.win32 import kernel32

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
