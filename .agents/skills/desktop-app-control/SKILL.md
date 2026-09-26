---
name: desktop-app-control
description: Controls Windows desktop applications, system settings, and processes. Handles app launching, window management, media playback, volume control, taskbar interaction, screenshots, and process lifecycle. Includes PowerShell and WinAPI automation.
---

# Desktop & App Control Skill

## Purpose
Enables JARVIS to control any Windows desktop application, system process, or UI element — from launching apps and managing windows to adjusting volume, taking screenshots, and killing processes.

## When to Activate
- "Open/close/minimize/maximize <app>"
- "Take a screenshot"
- "Kill the process <name>"
- "Increase/decrease volume"
- "Set volume to X%"
- "Lock the screen / sleep the computer"
- "Check what's running"
- "Switch to window <name>"

## Core Workflows

### 1. Launch an Application
```powershell
# Approach A — using Start-Process (PowerShell)
Start-Process "notepad.exe"

# Approach B — shell by name (searches PATH)
Start-Process "spotify"
Start-Process "chrome.exe"
Start-Process "code"   # VS Code
```

### 2. Kill a Process by Name
```powershell
Stop-Process -Name "notepad" -Force
# or
taskkill /IM "chrome.exe" /F
```

### 3. Volume Control
```powershell
# Set volume to 50% using nircmd (if installed)
nircmd.exe setsysvolume 32767

# Using PowerShell COM
$wshShell = New-Object -ComObject WScript.Shell
$wshShell.SendKeys([char]174)  # Volume Down
$wshShell.SendKeys([char]175)  # Volume Up
$wshShell.SendKeys([char]173)  # Mute/Unmute
```

### 4. Screenshot
```powershell
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Screen]::PrimaryScreen | Out-Null
$bitmap = [System.Drawing.Bitmap]::new([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,
    [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen(0, 0, 0, 0, $bitmap.Size)
$bitmap.Save("C:\Users\$env:USERNAME\Desktop\jarvis_screenshot.png")
```

### 5. Screen Lock / Sleep
```powershell
# Lock screen
rundll32.exe user32.dll,LockWorkStation

# Sleep
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::SetSuspendState("Suspend", $false, $false)
```

### 6. Window Focus / Switch
```powershell
# Bring app to foreground by process name
$app = Get-Process "notepad" -ErrorAction SilentlyContinue
if ($app) {
    $hwnd = $app.MainWindowHandle
    [void][System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer(
        (Add-Type -PassThru -Name Win32 -Namespace Native -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);')::SetForegroundWindow, [type]$hwnd
    )
}
```

## Best Practices & Safety Invariants
- Never kill system-critical processes (`lsass.exe`, `csrss.exe`, `svchost.exe`).
- Always confirm before closing unsaved application state.
- Log every app-launch or process-kill action to JARVIS event stream `desktop.action`.
