#!/bin/bash
set -e
cd "$(dirname "$0")"
pip3 install -r requirements.txt || true
python3 -m py_compile main.py cli.py gui_module.py
echo "Linux syntax check passed."
echo "Windows .exe: run build_windows.ps1 on a Windows machine."
