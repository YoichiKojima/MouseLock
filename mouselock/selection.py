from mouselock.monitors import (
    get_monitor_bounds_at,
    get_virtual_screen_bounds,
    restore_foreground,
)
from mouselock.mouse_clip import lock_mouse_to_area, restore_saved_lock, unlock_mouse
from mouselock.mouse_hook import (
    install_mouse_hook,
    start_mouse_pump,
    stop_mouse_pump,
    uninstall_mouse_hook,
)
from mouselock.overlay import (
    cancel_overlay_fade,
    create_selection_overlay,
    destroy_selection_overlay,
    fade_out_overlay,
    raise_overlay_windows,
    update_layered_overlay,
)
from mouselock.state import (
    hook_active,
    hook_dragging,
    mouse_clip,
    mouse_events,
    mouse_hook,
    root,
    saved_lock_rect,
    selection,
    selection_session,
)
from mouselock.win32 import user32


def end_selection_mode(restore_focus=True, animate=True):
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

    if animate and selection.get("overlay_monitors"):
        def finish():
            destroy_selection_overlay()
            if foreground:
                root.after(50, lambda: restore_foreground(foreground))

        fade_out_overlay(finish)
        return

    destroy_selection_overlay()

    if foreground:
        root.after(50, lambda: restore_foreground(foreground))


def close_overlay(restore_focus=True):
    end_selection_mode(restore_focus=restore_focus, animate=False)


def end_selection_session(restore_original=False):
    should_restore = restore_original and selection_session["restore_on_cancel"]
    selection_session["restore_on_cancel"] = False
    was_active = selection["active"]
    end_selection_mode(restore_focus=True)
    if should_restore and was_active and saved_lock_rect["rect"] is not None:
        root.after(50, restore_saved_lock)


def start_area_selection():
    if selection["active"]:
        end_selection_session(restore_original=True)
        return

    cancel_overlay_fade()
    destroy_selection_overlay()

    selection_session["restore_on_cancel"] = mouse_clip["rect"] is not None

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
        selection["last_cutout"] = None
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
    raise_overlay_windows()
    print("Click and drag to select an area. Press Esc to cancel.")
