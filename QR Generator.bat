@echo off
cd /d "%~dp0"
start "" pythonw qr_generator.py
if errorlevel 1 (
  echo Could not start. Trying the py launcher...
  start "" pyw qr_generator.py
)
