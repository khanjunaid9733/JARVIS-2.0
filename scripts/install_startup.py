"""JARVIS 2.0 — Windows Startup Resident Installer (Option 3).

Registers JARVIS 2.0 to boot silently in the background on Windows login.
Pre-warms the kernel, event log, capability providers, and Global Hotkey (Alt + J).
"""

import os
from pathlib import Path
import sys


def get_startup_folder() -> Path:
    """Return user's Windows Startup directory."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA environment variable not found.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def get_pythonw_path() -> Path:
    """Find pythonw.exe in the current Python environment for windowless execution."""
    current_python = Path(sys.executable)
    pythonw = current_python.parent / "pythonw.exe"
    if pythonw.is_file():
        return pythonw
    return current_python


def install_startup(port: int = 7777) -> Path:
    """Create a silent VBScript launcher in Windows Startup."""
    startup_dir = get_startup_folder()
    startup_dir.mkdir(parents=True, exist_ok=True)
    target_vbs = startup_dir / "JARVIS_2_0_Resident.vbs"

    repo_root = Path(__file__).resolve().parent.parent
    pythonw = get_pythonw_path()

    # VBScript executes pythonw silently with WindowStyle 0 (hidden)
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{repo_root}"
WshShell.Run """{pythonw}""" & " -c ""import sys; sys.path.insert(0, 'src'); from jarvis.ui.server import run_server; run_server({port})""", 0, False
'''
    target_vbs.write_text(vbs_content, encoding="utf-8")
    return target_vbs


def uninstall_startup() -> bool:
    """Remove the silent VBScript launcher from Windows Startup."""
    startup_dir = get_startup_folder()
    target_vbs = startup_dir / "JARVIS_2_0_Resident.vbs"
    if target_vbs.exists():
        target_vbs.unlink()
        return True
    return False


def is_installed() -> bool:
    """Check if startup launcher is currently installed."""
    startup_dir = get_startup_folder()
    target_vbs = startup_dir / "JARVIS_2_0_Resident.vbs"
    return target_vbs.exists()


def create_desktop_launcher(port: int = 7777) -> Path:
    """Create a 1-click silent background launcher on user's Desktop."""
    desktop_dir = Path.home() / "Desktop"
    target_vbs = desktop_dir / "JARVIS_Silent_Background.vbs"
    repo_root = Path(__file__).resolve().parent.parent
    pythonw = get_pythonw_path()

    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{repo_root}"
WshShell.Run """{pythonw}""" & " -c ""import sys; sys.path.insert(0, 'src'); from jarvis.ui.server import run_server; run_server({port})""", 0, False
WshShell.Popup "JARVIS 2.0 is now active in the background." & vbCrLf & vbCrLf & "- Say 'Hey JARVIS' anywhere" & vbCrLf & "- Press Alt+J to summon holographic HUD", 4, "JARVIS 2.0 Resident", 64
'''
    target_vbs.write_text(vbs_content, encoding="utf-8")
    return target_vbs


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        removed = uninstall_startup()
        print(f"Startup launcher removed: {removed}")
    elif len(sys.argv) > 1 and sys.argv[1] == "--status":
        print(f"Installed in Windows Startup: {is_installed()}")
    else:
        installed_path = install_startup()
        print(f"JARVIS 2.0 Resident launcher successfully installed at: {installed_path}")
        desktop_path = create_desktop_launcher()
        print(f"JARVIS 2.0 Desktop launcher created at: {desktop_path}")

