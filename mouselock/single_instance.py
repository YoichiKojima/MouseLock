import ctypes

from mouselock.win32 import kernel32

MUTEX_NAME = "Local\\MouseLock.SingleInstance"
ERROR_ALREADY_EXISTS = 183

_mutex = None


def acquire_instance():
    global _mutex
    _mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    return kernel32.GetLastError() != ERROR_ALREADY_EXISTS
