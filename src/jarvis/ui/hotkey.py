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


def _find_window_by_title(title_substring: str) -> Optional[int]:
    """Find a top-level window whose title contains title_substring."""
    if sys.platform != "win32":
        return None
    try:
        user32 = ctypes.windll.user32
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )
        found: list[int] = []

        def _enum(hwnd: ctypes.wintypes.HWND, _lParam: ctypes.wintypes.LPARAM) -> bool:
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if title_substring.lower() in buf.value.lower():
                    found.append(hwnd)
            return True

        user32.EnumWindows(EnumWindowsProc(_enum), 0)
        return found[0] if found else None
    except Exception:
        return None


def launch_or_focus_hud(port: int = 7777) -> None:
    """Launch or bring the JARVIS HUD to the foreground and trigger voice wake.

    If the HUD overlay window is already open:
    1. Restores and brings it to foreground (SetForegroundWindow + SetWindowPos HWND_TOPMOST).
    2. Sends POST /api/wake to immediately engage voice listening.

    If not yet open:
    Launches the transparent desktop HUD overlay.
    """
    if sys.platform != "win32":
        return

    hwnd = _find_window_by_title("J.A.R.V.I.S.")
    if hwnd:
        try:
            user32 = ctypes.windll.user32
            HWND_TOPMOST = ctypes.wintypes.HWND(-1)
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_SHOWWINDOW = 0x0040
            SW_RESTORE = 9

            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
            )
        except Exception:
            pass

        # Trigger acoustic / voice listening on HUD
        try:
            import urllib.request
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/wake",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=0.8)
        except Exception:
            pass
        return

    # Window not running — launch fresh overlay
    launch_transparent_hud(port=port)


def launch_transparent_hud(port: int = 7777) -> None:
    """Launch the JARVIS overlay in a transparent, always-on-top chromeless window.

    Uses Edge or Chrome in --app mode with the overlay URL, then pins the window
    as always-on-top using Win32 SetWindowPos(HWND_TOPMOST). The transparent
    background is achieved via the overlay CSS (background: transparent).
    """
    url = f"http://127.0.0.1:{port}/overlay"
    if sys.platform != "win32":
        return

    try:
        # Find Edge or Chrome
        browser_path: Optional[str] = None
        for candidate in [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]:
            if os.path.exists(candidate):
                browser_path = candidate
                break

        if not browser_path:
            os.system(f'start "" "{url}"')
            return

        profile_dir = os.path.expandvars(r"%LocalAppData%\JARVIS\overlay_browser_data")
        try:
            os.makedirs(profile_dir, exist_ok=True)
        except Exception:
            pass

        # Launch in app mode — chromeless, dedicated profile so it always spawns
        subprocess.Popen([
            browser_path,
            f"--app={url}",
            f"--user-data-dir={profile_dir}",
            "--window-size=1920,1080",
            "--window-position=0,0",
            "--disable-features=TranslateUI",
            "--disable-infobars",
            "--hide-crash-restore-bubble",
        ])

        # Give the window time to spawn, then pin it always-on-top
        _pin_thread = threading.Thread(
            target=_find_and_pin_topmost,
            args=("J.A.R.V.I.S.",),
            daemon=True,
        )
        _pin_thread.start()

    except Exception:
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception:
            pass


def _find_and_pin_topmost(title_substring: str, max_wait_seconds: int = 10) -> None:
    """Search for a window containing the title substring and pin it as always-on-top.

    Uses Win32 EnumWindows + SetWindowPos(HWND_TOPMOST) via ctypes.
    """
    import time

    if sys.platform != "win32":
        return

    try:
        user32 = ctypes.windll.user32

        # Win32 constants
        HWND_TOPMOST = ctypes.wintypes.HWND(-1)
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )

        target_hwnd: Optional[ctypes.wintypes.HWND] = None
        deadline = time.monotonic() + max_wait_seconds

        while time.monotonic() < deadline:
            found_handles: list[int] = []

            def _enum_callback(hwnd: ctypes.wintypes.HWND, _lParam: ctypes.wintypes.LPARAM) -> bool:
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    if title_substring.lower() in buf.value.lower():
                        found_handles.append(hwnd)
                return True  # Continue enumeration

            user32.EnumWindows(EnumWindowsProc(_enum_callback), 0)

            if found_handles:
                target_hwnd = found_handles[0]
                break

            time.sleep(0.5)

        if target_hwnd is not None:
            # Pin as always-on-top
            user32.SetWindowPos(
                target_hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
            )
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
