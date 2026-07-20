# TrainerHub Windows Build Script
# Run in PowerShell as Administrator or normal user

$ErrorActionPreference = "Stop"

function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

# 1. Ensure Python 3.11
if (-not (Test-Command python)) {
    Write-Host "Python not found. Downloading Python 3.11..."
    $pythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $installer = "$env:TEMP\python-3.11.9-amd64.exe"
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installer
    Start-Process -FilePath $installer -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User")
}

# 2. Ensure pip deps
Write-Host "Installing Python packages..."
python -m pip install --upgrade pip setuptools wheel
python -m pip install pyinstaller==5.13.2 pymem pywin32 pywin32-ctypes

# 3. Build
Write-Host "Building TrainerHub as OneDir (stable)..."
python -m PyInstaller TrainerHub.spec --clean --noconfirm

# 4. Result
$exePath = "dist\TrainerHub\TrainerHub.exe"
if (Test-Path $exePath) {
    $size = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
    Write-Host "SUCCESS: $exePath ($size MB)"
    Write-Host "Run it from: dist\TrainerHub\"
} else {
    Write-Host "FAILED: $exePath not found."
    Write-Host "Check the PyInstaller output above for errors."
}
