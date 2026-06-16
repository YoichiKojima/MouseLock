import ctypes

from mouselock.config import WH_MOUSE_LL, WM_LBUTTONDOWN, WM_LBUTTONUP
from mouselock.monitors import get_cursor_pos
from mouselock.overlay import raise_overlay_windows
from mouselock.state import (
    hook_active,
    hook_dragging,
    mouse_events,
    mouse_hook,
    selection,
)
from mouselock.win32 import HOOKPROC, MSLLHOOKSTRUCT, cross_cursor, user32


def stop_mouse_pump():
    from mouselock.state import root

    job = selection.get("poll_job")
    if job is not None:
        root.after_cancel(job)
    selection["poll_job"] = None
    mouse_events.clear()


def pump_mouse_events():
    from mouselock.state import root

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

    user32.SetCursor(cross_cursor)
    raise_overlay_windows()

    selection["poll_job"] = root.after(8, pump_mouse_events)


def start_mouse_pump():
    from mouselock.state import root

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
