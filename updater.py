"""TrainerHub Auto-Updater - downloads and installs updates automatically."""
import os
import sys
import json
import shutil
import tempfile
import threading
import urllib.request
import zipfile
import subprocess
import time

APP_VERSION = '0.5.2'
UPDATE_API = 'https://sayfespace.online/trainerhub/api/version.php'
USER_AGENT = f'TrainerHub/{APP_VERSION}'


def version_greater(a, b):
    try:
        return tuple(map(int, a.split('.'))) > tuple(map(int, b.split('.')))
    except Exception:
        return a != b


def get_update_info(timeout=10):
    try:
        req = urllib.request.Request(UPDATE_API, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None


def download_file(url, dest, progress_callback=None):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            block = 65536
            downloaded = 0
            with open(dest, 'wb') as f:
                while True:
                    chunk = resp.read(block)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(int(downloaded * 100 / total))
        return True
    except Exception as e:
        print(f"Download error: {e}")
        return False


def install_update(zip_path, app_dir, exe_path):
    """
    Windows-only: extract update zip to temp, then spawn helper process that
    waits for this process to exit, replaces files, and relaunches TrainerHub.
    """
    if sys.platform != 'win32':
        return False

    extract_dir = tempfile.mkdtemp(prefix='trainerhub_update_')
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)

        # Find the new TrainerHub folder inside extracted zip
        extracted_contents = [d for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
        new_app_dir = os.path.join(extract_dir, extracted_contents[0]) if extracted_contents else extract_dir

        # Write update helper script to temp
        helper_bat = os.path.join(tempfile.gettempdir(), 'trainerhub_update_helper.bat')
        old_dir = app_dir
        pid = os.getpid()
        log = os.path.join(tempfile.gettempdir(), 'trainerhub_update.log')

        with open(helper_bat, 'w', encoding='utf-8') as f:
            f.write(f"""@echo off
>"{log}" echo Update started at %date% %time%
timeout /t 2 /nobreak > nul
:waitloop
tasklist /FI "PID eq {pid}" 2>NUL | findstr "{pid}" >NUL
if %errorlevel% == 0 (
    timeout /t 1 /nobreak > nul
    goto waitloop
)
>>"{log}" echo old process gone
if exist "{old_dir}" (
    rmdir /S /Q "{old_dir}.old" 2>NUL
    move /Y "{old_dir}" "{old_dir}.old" >>"{log}" 2>&1
)
xcopy /E /I /Y "{new_app_dir}" "{old_dir}" >>"{log}" 2>&1
start "" "{exe_path}"
del /F /Q "{helper_bat}" >>"{log}" 2>&1
""")

        subprocess.Popen(['cmd.exe', '/c', helper_bat], shell=False,
                          creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                          close_fds=True)
        return True
    except Exception as e:
        print(f"Install error: {e}")
        return False


def check_and_install_update(parent_app=None, progress_callback=None, finished_callback=None):
    """
    Non-blocking update check. If update available, downloads and installs it.
    parent_app can be used to call UI callbacks on the main thread.
    """
    def run():
        info = get_update_info()
        if not info or not info.get('success'):
            return
        latest = info.get('version', APP_VERSION)
        if not version_greater(latest, APP_VERSION):
            return

        zip_url = info.get('download_url') or info.get('installer_url')
        if not zip_url:
            return

        # If zip_url is exe, prefer download_url (zip) from API
        if zip_url.endswith('.exe'):
            zip_url = info.get('download_url', zip_url)

        zip_path = os.path.join(tempfile.gettempdir(), f'TrainerHub-update-{latest}.zip')

        def cb(p):
            if progress_callback:
                if parent_app:
                    parent_app.root.after(0, lambda: progress_callback(p))
                else:
                    progress_callback(p)

        if not download_file(zip_url, zip_path, cb):
            if finished_callback:
                if parent_app:
                    parent_app.root.after(0, lambda: finished_callback(False, 'Download fehlgeschlagen'))
                else:
                    finished_callback(False, 'Download fehlgeschlagen')
            return

        app_dir = os.path.dirname(os.path.dirname(sys.executable))
        exe_path = sys.executable

        if install_update(zip_path, app_dir, exe_path):
            if finished_callback:
                if parent_app:
                    parent_app.root.after(0, lambda: finished_callback(True, 'Update bereit. TrainerHub wird neu gestartet.'))
                else:
                    finished_callback(True, 'Update bereit. TrainerHub wird neu gestartet.')
            # Give UI a moment to show message, then exit
            time.sleep(1.5)
            sys.exit(0)
        else:
            if finished_callback:
                if parent_app:
                    parent_app.root.after(0, lambda: finished_callback(False, 'Installation fehlgeschlagen'))
                else:
                    finished_callback(False, 'Installation fehlgeschlagen')

    threading.Thread(target=run, daemon=True).start()


if __name__ == '__main__':
    print('Update info:', get_update_info())
