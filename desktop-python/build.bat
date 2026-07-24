@echo off
echo Building TrainerHub Desktop for Windows...
python -m pip install -r requirements.txt
python -m PyInstaller --onefile --name TrainerHub --icon=icon.ico main.py
pause
