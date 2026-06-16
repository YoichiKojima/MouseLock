import tkinter as tk
import ctypes

root = tk.Tk()
root.withdraw()

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
    "fade_job": None,
    "fade_alpha": 0,
    "last_cutout": None,
    "state": None,
    "on_press": None,
    "on_drag": None,
    "on_release": None,
    "poll_job": None,
}
session_state = {"locked": False}

overlay_wndproc_ref = None
overlay_class_registered = False
