@echo off
setlocal
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
"%~dp0.venv\Scripts\python.exe" -m jarvis %*
