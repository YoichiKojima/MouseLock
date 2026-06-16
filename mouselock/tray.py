import ctypes
import sys
from pathlib import Path

from mouselock.state import root
from mouselock.win32 import POINT, WNDCLASSW, WNDPROC, kernel32, user32

shell32 = ctypes.windll.shell32

TRAY_CLASS_NAME = "MouseLockTray"
TRAY_ICON_ID = 1
WM_TRAYICON = 0x0400 + 1
WM_COMMAND = 0x0111
WM_RBUTTONUP = 0x0205
WM_LBUTTONDBLCLK = 0x0203
WM_NULL = 0x0000

NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RIGHTBUTTON = 0x0002
TPM_BOTTOMALIGN = 0x0020
TPM_LEFTALIGN = 0x0000

ID_SELECT = 1001
ID_TOGGLE = 1002
ID_EXIT = 1003

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040

WS_EX_TOOLWINDOW = 0x00000080
WS_POPUP = 0x80000000
HWND_MESSAGE = -3

tray_state = {
    "hwnd": None,
    "wndproc_ref": None,
    "class_registered": False,
    "icon_handle": None,
    "on_select": None,
    "on_toggle": None,
    "on_exit": None,
}


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("hWnd", ctypes.c_void_p),
        ("uID", ctypes.c_uint32),
        ("uFlags", ctypes.c_uint32),
        ("uCallbackMessage", ctypes.c_uint32),
        ("hIcon", ctypes.c_void_p),
        ("szTip", ctypes.c_wchar * 128),
    ]


def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def _command_id(wparam):
    return int(wparam) & 0xFFFF


def _show_context_menu(hwnd):
    hmenu = user32.CreatePopupMenu()
    user32.AppendMenuW(hmenu, MF_STRING, ID_SELECT, "Select area\tAlt+C")
    user32.AppendMenuW(hmenu, MF_STRING, ID_TOGGLE, "Toggle lock\tAlt+X")
    user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
    user32.AppendMenuW(hmenu, MF_STRING, ID_EXIT, "Exit")

    point = POINT()
    user32.GetCursorPos(ctypes.byref(point))
    user32.SetForegroundWindow(hwnd)
    user32.TrackPopupMenu(
        hmenu,
        TPM_RIGHTBUTTON | TPM_BOTTOMALIGN | TPM_LEFTALIGN,
        point.x,
        point.y,
        0,
        hwnd,
        None,
    )
    user32.PostMessageW(hwnd, WM_NULL, 0, 0)
    user32.DestroyMenu(hmenu)


def _ensure_tray_window():
    if tray_state["hwnd"]:
        return tray_state["hwnd"]

    @WNDPROC
    def tray_wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            event = int(lparam)
            if event == WM_RBUTTONUP:
                _show_context_menu(hwnd)
                return 0
            if event == WM_LBUTTONDBLCLK and tray_state["on_toggle"]:
                root.after(0, tray_state["on_toggle"])
                return 0
        if msg == WM_COMMAND:
            cmd = _command_id(wparam)
            if cmd == ID_SELECT and tray_state["on_select"]:
                root.after(0, tray_state["on_select"])
            elif cmd == ID_TOGGLE and tray_state["on_toggle"]:
                root.after(0, tray_state["on_toggle"])
            elif cmd == ID_EXIT and tray_state["on_exit"]:
                root.after(0, tray_state["on_exit"])
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    tray_state["wndproc_ref"] = tray_wndproc

    if not tray_state["class_registered"]:
        wc = WNDCLASSW()
        wc.lpfnWndProc = tray_state["wndproc_ref"]
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = TRAY_CLASS_NAME
        user32.RegisterClassW(ctypes.byref(wc))
        tray_state["class_registered"] = True

    hwnd = user32.CreateWindowExW(
        WS_EX_TOOLWINDOW,
        TRAY_CLASS_NAME,
        "MouseLock",
        WS_POPUP,
        0,
        0,
        0,
        0,
        HWND_MESSAGE,
        None,
        kernel32.GetModuleHandleW(None),
        None,
    )
    if not hwnd:
        print(f"Tray window failed, error={ctypes.get_last_error()}")
        return None

    tray_state["hwnd"] = hwnd
    return hwnd


def setup_tray(on_select, on_toggle, on_exit):
    tray_state["on_select"] = on_select
    tray_state["on_toggle"] = on_toggle
    tray_state["on_exit"] = on_exit

    hwnd = _ensure_tray_window()
    if not hwnd:
        return False

    icon_path = str(resource_path("assets", "icon.ico"))
    icon_handle = user32.LoadImageW(
        None,
        icon_path,
        IMAGE_ICON,
        0,
        0,
        LR_LOADFROMFILE | LR_DEFAULTSIZE,
    )
    if not icon_handle:
        print(f"Tray icon failed to load from {icon_path}, error={ctypes.get_last_error()}")
        return False

    tray_state["icon_handle"] = icon_handle

    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = TRAY_ICON_ID
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = WM_TRAYICON
    nid.hIcon = icon_handle
    nid.szTip = "Mouse Lock"

    if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
        print(f"Shell_NotifyIconW failed, error={ctypes.get_last_error()}")
        return False

    return True


def remove_tray():
    hwnd = tray_state.get("hwnd")
    if hwnd:
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = TRAY_ICON_ID
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        user32.DestroyWindow(hwnd)

    icon_handle = tray_state.get("icon_handle")
    if icon_handle:
        user32.DestroyIcon(icon_handle)

    tray_state["hwnd"] = None
    tray_state["icon_handle"] = None
    tray_state["on_select"] = None
    tray_state["on_toggle"] = None
    tray_state["on_exit"] = None
