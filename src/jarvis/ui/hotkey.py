from __future__ import annotations

"""Native Windows Win32 Global Hotkey Listener (Option 1).

Registers a system-wide hotkey (default: Alt + J) using ctypes and user32.dll
with zero external dependencies. When triggered, it summons or focuses the
JARVIS 2.0 Holographic HUD in standalone desktop app mode.
"""

import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import threading
from typing import Callable, Optional

# Win32 Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
VK_J = 0x4A  # Virtual-Key code for 'J'
WM_HOTKEY = 0x0312
HOTKEY_ID = 0x7777


def launch_or_focus_hud(port: int = 7777) -> None:
    """Launch or bring the JARVIS HUD to the foreground in chromeless app mode."""
    url = f"http://127.0.0.1:{port}"
    if sys.platform != "win32":
        return

    # Attempt msedge app mode first, then chrome, then fallback to explorer/start
    try:
        # Edge App mode
        edge_path = os.path.expandvars(
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
        )
        if not os.path.exists(edge_path):
            edge_path = os.path.expandvars(
                r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
            )

        if os.path.exists(edge_path):
            subprocess.Popen([edge_path, f"--app={url}", "--window-size=1280,840"])
            return

        # Chrome App mode fallback
        chrome_path = os.path.expandvars(
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
        )
        if os.path.exists(chrome_path):
            subprocess.Popen([chrome_path, f"--app={url}", "--window-size=1280,840"])
            return

        # Generic system URL open
        os.system(f'start "" "{url}"')
    except Exception:
        pass


class GlobalHotkeyListener:
    """Listens for a global hotkey across Windows in a background daemon thread."""

    def __init__(
        self,
        callback: Optional[Callable[[], None]] = None,
        port: int = 7777,
        modifiers: int = MOD_ALT | MOD_NOREPEAT,
        vk_code: int = VK_J,
    ) -> None:
        self.port = port
        self.callback = callback or (lambda: launch_or_focus_hud(self.port))
        self.modifiers = modifiers
        self.vk_code = vk_code
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._thread_id: Optional[int] = None

    def start(self) -> bool:
        """Start hotkey listener in background thread."""
        if sys.platform != "win32":
            return False

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def _run(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()

        registered = user32.RegisterHotKey(
            None, HOTKEY_ID, self.modifiers, self.vk_code
        )
        if not registered:
            # If Alt+J is taken, fallback to Ctrl+Shift+J
            self.modifiers = MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT
            registered = user32.RegisterHotKey(
                None, HOTKEY_ID, self.modifiers, self.vk_code
            )

        if not registered:
            return

        try:
            msg = wintypes.MSG()
            while not self._stop_event.is_set():
                res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if res <= 0:
                    break
                if msg.message == WM_HOTKEY:
                    try:
                        self.callback()
                    except Exception:
                        pass
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)

    def stop(self) -> None:
        """Post quit message and unregister hotkey."""
        self._stop_event.set()
        if sys.platform == "win32" and self._thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass
