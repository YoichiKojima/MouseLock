import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import keyboard

from mouselock.hotkey_manager import validate_hotkey
from mouselock.settings_store import load, save
from mouselock.state import root
from mouselock.windows_startup import set_enabled as set_windows_startup
from mouselock.win32 import user32

_dialog = None


def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def _set_dialog_icon(dialog):
    icon_path = resource_path("assets", "icon.ico")
    try:
        from PIL import ImageTk
        from PIL.IcoImagePlugin import IcoFile

        with icon_path.open("rb") as f:
            ico = IcoFile(f)
            images = [
                ico.getimage((size, size)).copy()
                for size in (16, 32, 48)
                if (size, size) in ico.sizes()
            ]
        if images:
            photos = [ImageTk.PhotoImage(img, master=dialog) for img in images]
            dialog.iconphoto(True, *photos)
            dialog._icon_photos = photos
            return
    except Exception:
        pass

    try:
        dialog.iconbitmap(str(icon_path))
    except tk.TclError:
        pass


def _set_status(label, text):
    label.config(text=text)


def _bring_to_front(dialog):
    dialog.deiconify()
    dialog.lift()
    dialog.attributes("-topmost", True)
    dialog.update_idletasks()
    try:
        user32.SetForegroundWindow(dialog.winfo_id())
    except Exception:
        pass
    dialog.focus_force()
    dialog.after(200, lambda: dialog.attributes("-topmost", False))


def _record_hotkey(target_var, status_label, record_btn, all_record_btns):
    for btn in all_record_btns:
        btn.config(state=tk.DISABLED)
    _set_status(status_label, "Press a key combination, then release...")

    def worker():
        try:
            hotkey = keyboard.read_hotkey(suppress=False)
        except Exception:
            hotkey = None

        def finish():
            if hotkey:
                target_var.set(hotkey)
            _set_status(status_label, "")
            for btn in all_record_btns:
                btn.config(state=tk.NORMAL)

        root.after(0, finish)

    threading.Thread(target=worker, daemon=True).start()


def show_settings_dialog(on_saved):
    global _dialog

    if _dialog is not None:
        try:
            if _dialog.winfo_exists():
                _bring_to_front(_dialog)
                return
        except tk.TclError:
            pass
        _dialog = None

    settings = load()

    dialog = tk.Toplevel(root)
    _dialog = dialog
    dialog.title("Settings")
    dialog.resizable(False, False)
    _set_dialog_icon(dialog)

    frame = ttk.Frame(dialog, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")

    select_var = tk.StringVar(value=settings["select_hotkey"])
    toggle_var = tk.StringVar(value=settings["toggle_hotkey"])
    startup_var = tk.BooleanVar(value=settings["start_with_windows"])
    status = ttk.Label(frame, text="")

    def make_row(row, label_text, var):
        ttk.Label(frame, text=label_text).grid(row=row, column=0, sticky="w", pady=(0, 8))
        entry = ttk.Entry(frame, textvariable=var, width=24, state="readonly")
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=(0, 8))
        record_btn = ttk.Button(
            frame,
            text="Change",
            command=lambda: _record_hotkey(var, status, record_btn, record_buttons),
        )
        record_btn.grid(row=row, column=2, pady=(0, 8))
        return record_btn

    record_buttons = [
        make_row(0, "Select area", select_var),
        make_row(1, "Toggle lock", toggle_var),
    ]

    ttk.Checkbutton(
        frame,
        text="Start with Windows",
        variable=startup_var,
    ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 8))

    status.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 12))

    button_row = ttk.Frame(frame)
    button_row.grid(row=4, column=0, columnspan=3, sticky="e")

    def close_dialog():
        global _dialog
        try:
            dialog.grab_release()
        except tk.TclError:
            pass
        dialog.destroy()
        _dialog = None

    def on_save():
        select_hotkey = select_var.get().strip().lower()
        toggle_hotkey = toggle_var.get().strip().lower()

        if select_hotkey == toggle_hotkey:
            messagebox.showerror(
                "Invalid hotkeys",
                "Select area and toggle lock must be different.",
                parent=dialog,
            )
            return

        for label, hotkey in (
            ("Select area", select_hotkey),
            ("Toggle lock", toggle_hotkey),
        ):
            ok, message = validate_hotkey(hotkey)
            if not ok:
                messagebox.showerror("Invalid hotkey", f"{label}: {message}", parent=dialog)
                return

        save(select_hotkey, toggle_hotkey, startup_var.get())
        try:
            set_windows_startup(startup_var.get())
        except OSError as exc:
            messagebox.showerror(
                "Startup setting failed",
                f"Could not update Windows startup:\n{exc}",
                parent=dialog,
            )
            return
        close_dialog()
        on_saved()

    ttk.Button(button_row, text="Cancel", command=close_dialog).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(button_row, text="Save", command=on_save).grid(row=0, column=1)

    dialog.protocol("WM_DELETE_WINDOW", close_dialog)
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() - width) // 2
    y = (dialog.winfo_screenheight() - height) // 2
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    _bring_to_front(dialog)
    dialog.grab_set()
