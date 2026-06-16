import ctypes

from mouselock.state import mouse_clip, root, saved_lock_rect
from mouselock.win32 import RECT, user32


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
