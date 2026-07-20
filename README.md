# TrainerHub Desktop App

Windows Desktop-App für TrainerHub. Lädt Spiele, Trainer und Cheats von sayfespace.online.

## Download

Jeder Push auf `main` baut automatisch eine Windows-EXE via GitHub Actions.

Siehe [Releases](https://github.com/zit0z/trainerhub/releases).

## Build lokal

```powershell
pip install pyinstaller pymem pywin32 pywin32-ctypes
pyinstaller TrainerHub.spec --clean --noconfirm
```

EXE liegt danach unter `dist\TrainerHub\TrainerHub.exe`.
