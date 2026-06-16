import ctypes

from mouselock.config import (
    AC_SRC_ALPHA,
    AC_SRC_OVER,
    BI_RGB,
    BORDER_DASH_OFF,
    BORDER_DASH_ON,
    DIB_RGB_COLORS,
    DIM_ALPHA,
    ERROR_CLASS_ALREADY_EXISTS,
    FADE_DURATION_MS,
    FADE_INTERVAL_MS,
    HWND_NOTOPMOST,
    HWND_TOPMOST,
    OVERLAY_CLASS_NAME,
    SWP_NOACTIVATE,
    SWP_SHOWWINDOW,
    SW_SHOWNA,
    ULW_ALPHA,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    WS_EX_TOPMOST,
    WS_POPUP,
)
from mouselock import state
from mouselock.monitors import enum_monitors
from mouselock.state import root, selection
from mouselock.win32 import (
    BITMAPINFO,
    BITMAPINFOHEADER,
    BLENDFUNCTION,
    POINT,
    SIZE,
    WNDCLASSW,
    WNDPROC,
    cross_cursor,
    gdi32,
    kernel32,
    user32,
)


def dash_visible(pos):
    period = BORDER_DASH_ON + BORDER_DASH_OFF
    return (pos // period) % 2 == 0


def build_overlay_bitmap(width, height, cutout=None, fade_alpha=255):
    dim_alpha = (DIM_ALPHA * max(0, min(255, int(fade_alpha)))) // 255
    pixel = bytes([0, 0, 0, dim_alpha])
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

    border_alpha = max(0, min(255, int(fade_alpha)))
    white = bytes([255, 255, 255, border_alpha])
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


def raise_overlay_windows():
    for overlay in selection.get("overlay_monitors") or []:
        hwnd = overlay["hwnd"]
        if not hwnd or not user32.IsWindow(hwnd):
            continue
        left = overlay["left"]
        top = overlay["top"]
        width = overlay["width"]
        height = overlay["height"]
        flags = SWP_NOACTIVATE | SWP_SHOWWINDOW
        user32.SetWindowPos(
            hwnd, HWND_NOTOPMOST, int(left), int(top), int(width), int(height), flags
        )
        user32.SetWindowPos(
            hwnd, HWND_TOPMOST, int(left), int(top), int(width), int(height), flags
        )


def update_one_layered_overlay(overlay, cutout=None, fade_alpha=None):
    hwnd = overlay["hwnd"]
    width = overlay["width"]
    height = overlay["height"]
    if fade_alpha is None:
        fade_alpha = selection.get("fade_alpha", 255)
    buf = build_overlay_bitmap(width, height, cutout, fade_alpha)

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


def update_layered_overlay(cutout=None, fade_alpha=None):
    if cutout is not None:
        selection["last_cutout"] = cutout
    elif not selection.get("dragging"):
        selection["last_cutout"] = None

    effective_cutout = cutout
    if effective_cutout is None and selection.get("dragging"):
        effective_cutout = selection.get("last_cutout")

    if fade_alpha is None:
        fade_alpha = selection.get("fade_alpha", 255)

    for overlay in selection.get("overlay_monitors") or []:
        local_cutout = monitor_cutout(overlay, effective_cutout)
        update_one_layered_overlay(overlay, local_cutout, fade_alpha)

    raise_overlay_windows()


def cancel_overlay_fade():
    job = selection.get("fade_job")
    if job is not None:
        root.after_cancel(job)
    selection["fade_job"] = None


def run_overlay_fade(target_alpha, on_complete=None):
    cancel_overlay_fade()
    if not selection.get("overlay_monitors"):
        if on_complete:
            on_complete()
        return

    start_alpha = selection.get("fade_alpha", 0)
    steps = max(1, FADE_DURATION_MS // FADE_INTERVAL_MS)

    def tick(step=0):
        if not selection.get("overlay_monitors"):
            selection["fade_job"] = None
            if on_complete:
                on_complete()
            return

        if step >= steps:
            selection["fade_alpha"] = target_alpha
            update_layered_overlay(fade_alpha=target_alpha)
            selection["fade_job"] = None
            if on_complete:
                on_complete()
            return

        alpha = int(start_alpha + (target_alpha - start_alpha) * (step + 1) / steps)
        selection["fade_alpha"] = alpha
        update_layered_overlay(fade_alpha=alpha)
        selection["fade_job"] = root.after(
            FADE_INTERVAL_MS, lambda s=step + 1: tick(s)
        )

    tick()


def fade_in_overlay():
    selection["fade_alpha"] = 0
    selection["last_cutout"] = None
    update_layered_overlay(fade_alpha=0)
    run_overlay_fade(255)


def fade_out_overlay(on_complete):
    run_overlay_fade(0, on_complete=on_complete)


def destroy_selection_overlay():
    cancel_overlay_fade()
    for overlay in selection.get("overlay_monitors") or []:
        user32.DestroyWindow(overlay["hwnd"])
    selection["overlay_monitors"] = None
    selection["fade_alpha"] = 0
    selection["last_cutout"] = None
    state.overlay_windows = []


def ensure_overlay_window_class():
    if state.overlay_class_registered:
        return True

    @WNDPROC
    def overlay_wndproc(hwnd, msg, wparam, lparam):
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    state.overlay_wndproc_ref = overlay_wndproc
    wc = WNDCLASSW()
    wc.lpfnWndProc = state.overlay_wndproc_ref
    wc.hInstance = kernel32.GetModuleHandleW(None)
    wc.hCursor = cross_cursor
    wc.lpszClassName = OVERLAY_CLASS_NAME

    atom = user32.RegisterClassW(ctypes.byref(wc))
    if not atom and ctypes.get_last_error() != ERROR_CLASS_ALREADY_EXISTS:
        print(f"RegisterClassW failed, error={ctypes.get_last_error()}")
        return False

    state.overlay_class_registered = True
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
    selection["fade_alpha"] = 0
    selection["last_cutout"] = None

    for overlay in overlays:
        update_one_layered_overlay(overlay, fade_alpha=0)

    state.overlay_windows = [overlay["hwnd"] for overlay in overlays]
    fade_in_overlay()
    return overlays
