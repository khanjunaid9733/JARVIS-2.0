' JARVIS 2.0 Silent Background Desktop Launcher
' Double-click to launch JARVIS as a background application with 0 terminal windows.
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
ScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

WshShell.CurrentDirectory = ScriptDir
WshShell.Run "python -m jarvis app --background", 0, False
