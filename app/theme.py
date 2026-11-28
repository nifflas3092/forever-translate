"""Window helpers: file locations, screen scaling and the app icon."""

import os
import sys
import tkinter as tk

# Where bundled files (the icon) live. Inside the .exe they are unpacked to a
# temporary folder; when run from source they sit next to this file.
RESOURCES = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

# Where the user's own files (config.json) live: next to the .exe, or next to
# the source files.
if getattr(sys, "frozen", False):
    USER_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    USER_DIR = os.path.dirname(os.path.abspath(__file__))

SCALE = 1.0  # screen scaling (1.0 = 100%), set by setup_dpi()


def px(n):
    """Pixels, adjusted for the screen's scaling."""
    return int(round(n * SCALE))


def make_dpi_aware():
    """Draw crisp at the real screen resolution instead of a tiny or blurry
    window. Must run before the window is created."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def setup_dpi(root):
    """Match text size to Windows' display scaling (100%, 125%, 150%...)."""
    global SCALE
    dpi = root.winfo_fpixels("1i")
    if sys.platform == "win32":
        root.tk.call("tk", "scaling", dpi / 72.0)
    SCALE = max(1.0, dpi / 96.0)
    return SCALE


def set_app_id():
    """Give the app its own taskbar entry (so it shows our icon, not Python's).
    Must run before the window is created."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ForeverTranslate.App")
        except Exception:
            pass


def set_window_icon(root):
    """The Ft speech-bubble icon on the title bar and taskbar."""
    try:
        if sys.platform == "win32":
            root.iconbitmap(default=os.path.join(RESOURCES, "assets", "icon.ico"))
        else:
            root._icon = tk.PhotoImage(file=os.path.join(RESOURCES, "assets", "icon.png"))
            root.iconphoto(True, root._icon)
    except Exception:
        pass
