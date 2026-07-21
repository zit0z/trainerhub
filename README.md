# TrainerHub Desktop

Windows-Desktop-App für TrainerHub — Singleplayer-Trainer für 300+ Spiele.

## Download

Fertige Windows-EXE: https://sayfespace.online/trainerhub/TrainerHub-windows.zip

## Features

- Modernes Dark UI mit Animationen
- 300+ unterstützte Spiele
- Memory-Scanner (2-Scan / 3-Scan)
- Pattern Learner
- SMAPI Bridge für Stardew Valley
- Savegame-Editor
- Favoriten, zuletzt verwendete Spiele
- Live-Log mit Export
- Auto-Update-Hinweis
- Account-/Premium-Status

## Login

- URL: https://sayfespace.online/trainerhub/
- Benutzer: `dom`
- Passwort: `TrainerHub2026!`

## Build

Lokal unter Windows:
```powershell
pip install pyinstaller==5.13.2 pymem pywin32 pywin32-ctypes
python -m PyInstaller TrainerHub.spec --clean --noconfirm
```
