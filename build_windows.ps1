# Build Windows EXE and create self-extracting installer for TrainerHub
param(
    [string]$Version = "0.5.0"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$DistDir = Join-Path $Root "dist"
$InstallerDir = Join-Path $Root "installer"
$SevenZip = "C:\Program Files\7-Zip\7z.exe"

Write-Host "=== TrainerHub Windows Build + Installer v$Version ===" -ForegroundColor Cyan

# 1. Build Python app via PyInstaller
Write-Host "Building EXE..." -ForegroundColor Yellow
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }

pyinstaller --noconfirm --onedir --name "TrainerHub" --windowed --icon "NONE" `
    --hidden-import ui_components `
    --hidden-import features `
    --hidden-import pattern_learner `
    --hidden-import savegame_trainers `
    --hidden-import sdv_savegame `
    --hidden-import stardew_bridge `
    --hidden-import cli `
    --exclude-module matplotlib `
    --exclude-module tkinter.test `
    --exclude-module scipy `
    --exclude-module pandas `
    --exclude-module numpy `
    "main.py"

if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# 2. Package dist into zip
Write-Host "Creating ZIP..." -ForegroundColor Yellow
$ZipName = "TrainerHub-windows.zip"
$ZipPath = Join-Path $Root $ZipName
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }

Compress-Archive -Path (Join-Path $DistDir "*") -DestinationPath $ZipPath -Force
Write-Host "Created: $ZipPath ($([math]::Round((Get-Item $ZipPath).Length / 1MB, 2)) MB)" -ForegroundColor Green

# 3. Create installer files
Write-Host "Preparing installer..." -ForegroundColor Yellow
if (Test-Path $InstallerDir) { Remove-Item -Recurse -Force $InstallerDir }
New-Item -ItemType Directory -Path $InstallerDir | Out-Null

# Copy dist content to installer staging
Copy-Item -Path (Join-Path $DistDir "TrainerHub") -Destination (Join-Path $InstallerDir "TrainerHub") -Recurse -Force

# Create install script
$InstallScript = @'
@echo off
echo === TrainerHub Installer ===
echo.
echo Installiere TrainerHub in %%LOCALAPPDATA%%\TrainerHub...
if not exist "%%LOCALAPPDATA%%\TrainerHub" mkdir "%%LOCALAPPDATA%%\TrainerHub"
xcopy /E /I /Y "TrainerHub" "%%LOCALAPPDATA%%\TrainerHub\TrainerHub"
if %errorlevel% neq 0 (
    echo Fehler beim Kopieren. Starte als Administrator neu.
    pause
    exit /b 1
)

:: Desktop shortcut
set "TARGET=%%LOCALAPPDATA%%\TrainerHub\TrainerHub\TrainerHub.exe"
set "SHORTCUT=%%USERPROFILE%%\Desktop\TrainerHub.lnk"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%TARGET%'; $s.WorkingDirectory = '%LOCALAPPDATA%\TrainerHub\TrainerHub'; $s.IconLocation = '%TARGET%,0'; $s.Save()"

:: Start Menu shortcut
set "STARTMENU=%%APPDATA%%\Microsoft\Windows\Start Menu\Programs"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTMENU%\TrainerHub.lnk'); $s.TargetPath = '%TARGET%'; $s.WorkingDirectory = '%LOCALAPPDATA%\TrainerHub\TrainerHub'; $s.IconLocation = '%TARGET%,0'; $s.Save()"

echo.
echo Installation abgeschlossen!
echo.
set /p STARTAPP="TrainerHub jetzt starten? (j/n): "
if /I "%%STARTAPP%%"=="j" start "" "%%TARGET%%"
exit /b 0
'@

Set-Content -Path (Join-Path $InstallerDir "install.bat") -Value $InstallScript -Encoding ASCII

# 4. Create 7z SFX installer if 7-Zip is available
if (Test-Path $SevenZip) {
    Write-Host "Creating SFX installer with 7-Zip..." -ForegroundColor Yellow
    $Archive = Join-Path $Root "installer.7z"
    $SfxModule = "C:\Program Files\7-Zip\7zS2.sfx"
    if (-not (Test-Path $SfxModule)) { $SfxModule = "C:\Program Files\7-Zip\7z.sfx" }

    # Create config for SFX
    $SfxConfig = @"
;!@Install@!UTF-8!
Title="TrainerHub v$Version"
BeginPrompt="Willst du TrainerHub v$Version installieren?\n\nDie App wird nach %LOCALAPPDATA%\TrainerHub kopiert."
RunProgram="install.bat"
;!@InstallEnd@!
"@
    Set-Content -Path (Join-Path $Root "sfx_config.txt") -Value $SfxConfig -Encoding UTF8

    # Pack installer dir
    if (Test-Path $Archive) { Remove-Item -Force $Archive }
    & $SevenZip a -mx9 -sfx:$SfxModule -r $Archive $InstallerDir\* | Out-Null

    # Rename to Setup.exe
    $SetupPath = Join-Path $Root "TrainerHub-Setup.exe"
    if (Test-Path $SetupPath) { Remove-Item -Force $SetupPath }
    Move-Item -Path $Archive -Destination $SetupPath -Force
    Write-Host "Created: $SetupPath ($([math]::Round((Get-Item $SetupPath).Length / 1MB, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "7-Zip not found, skipping SFX installer. ZIP-only." -ForegroundColor Red
}

Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host "Artifacts: $ZipPath, $SetupPath" -ForegroundColor Green
