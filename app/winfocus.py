"""Bring the WoW window to the front (Windows only).

This only switches windows, like clicking WoW on the taskbar. It never sends
keys or clicks to the game.
"""

import sys

WOW_TITLE = "World of Warcraft"


def focus_wow():
    """Returns True if the WoW window was found and brought to the front."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if buf.value == WOW_TITLE:
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(callback, 0)
    if not found:
        return False
    hwnd = found[0]
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    return bool(user32.SetForegroundWindow(hwnd))
