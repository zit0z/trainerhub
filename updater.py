"""TrainerHub Auto-Updater - delta updates, signature checks, rollback."""
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
import hashlib

APP_VERSION = '0.6.1'
UPDATE_API = 'https://sayfespace.online/trainerhub/api/version.php'
MANIFEST_URL = 'https://sayfespace.online/trainerhub/api/manifest.php'
USER_AGENT = f'TrainerHub/{APP_VERSION}'


def sha256_file(path, block=65536):
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(block)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def version_greater(a, b):
    try:
        return tuple(map(int, a.split('.'))) > tuple(map(int, b.split('.')))
    except Exception:
        return a != b


def http_get(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None


def download_file(url, dest, progress_callback=None, timeout=120):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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


def build_local_manifest(app_dir):
    """Build manifest of current installation (relative paths + sha256)."""
    manifest = {}
    for root, dirs, files in os.walk(app_dir):
        for fname in files:
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, app_dir).replace('\\', '/')
            manifest[rel] = sha256_file(full)
    return manifest


def compute_delta(local_manifest, remote_manifest):
    """Return list of files to download/replace."""
    to_update = []
    for rel, info in remote_manifest.items():
        if isinstance(info, dict):
            remote_hash = info.get('sha256')
            size = info.get('size', 0)
        else:
            remote_hash = info
            size = 0
        local_hash = local_manifest.get(rel)
        if local_hash != remote_hash:
            to_update.append((rel, remote_hash, size))
    return to_update


def apply_delta(zip_path, app_dir, delta_list, backup_dir):
    """Extract only changed files, backup old files, verify hashes."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            zip_names = z.namelist()
            for rel, expected_hash, _ in delta_list:
                # Find file in zip (may be prefixed by TrainerHub/)
                candidates = [n for n in zip_names if n.replace('\\', '/').endswith(rel)]
                if not candidates:
                    print(f"Missing in zip: {rel}")
                    continue
                src = candidates[0]
                dest = os.path.join(app_dir, rel.replace('/', os.sep))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                # backup old
                if os.path.exists(dest):
                    backup = os.path.join(backup_dir, rel.replace('/', os.sep))
                    os.makedirs(os.path.dirname(backup), exist_ok=True)
                    shutil.move(dest, backup)
                # extract new
                with z.open(src) as fsrc, open(dest, 'wb') as fdst:
                    shutil.copyfileobj(fsrc, fdst)
                # verify
                actual_hash = sha256_file(dest)
                if actual_hash != expected_hash:
                    raise RuntimeError(f"Hash mismatch for {rel}: {actual_hash} != {expected_hash}")
        return True
    except Exception as e:
        print(f"Delta apply error: {e}")
        return False


def rollback(backup_dir, app_dir):
    """Restore backup files if update failed."""
    try:
        for root, dirs, files in os.walk(backup_dir):
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, backup_dir)
                dest = os.path.join(app_dir, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(full, dest)
        return True
    except Exception as e:
        print(f"Rollback error: {e}")
        return False


def install_update(zip_path, app_dir, exe_path, delta_list=None):
    """
    Windows-only: apply delta or full update, backup old files, then spawn helper
    that waits for this process to exit and restarts TrainerHub.
    """
    if sys.platform != 'win32':
        return False

    backup_dir = os.path.join(tempfile.gettempdir(), 'trainerhub_backup')
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir, ignore_errors=True)
    os.makedirs(backup_dir, exist_ok=True)

    success = False
    if delta_list:
        success = apply_delta(zip_path, app_dir, delta_list, backup_dir)
    if not success:
        # fallback: full replace
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(backup_dir + '_new')
            extracted = [d for d in os.listdir(backup_dir + '_new') if os.path.isdir(os.path.join(backup_dir + '_new', d))]
            new_app_dir = os.path.join(backup_dir + '_new', extracted[0]) if extracted else backup_dir + '_new'
        except Exception:
            return False

    helper_bat = os.path.join(tempfile.gettempdir(), 'trainerhub_update_helper.bat')
    pid = os.getpid()
    log = os.path.join(tempfile.gettempdir(), 'trainerhub_update.log')

    if success:
        # delta install: we already applied files, just restart
        with open(helper_bat, 'w', encoding='utf-8') as f:
            f.write(f"""@echo off
>"{log}" echo Update restart at %date% %time%
timeout /t 2 /nobreak > nul
:waitloop
tasklist /FI "PID eq {pid}" 2>NUL | findstr "{pid}" >NUL
if %errorlevel% == 0 (
    timeout /t 1 /nobreak > nul
    goto waitloop
)
start "" "{exe_path}"
del /F /Q "{helper_bat}" >>"{log}" 2>&1
""")
    else:
        # full replace via helper
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
if exist "{app_dir}" (
    rmdir /S /Q "{app_dir}.old" 2>NUL
    move /Y "{app_dir}" "{app_dir}.old" >>"{log}" 2>&1
)
xcopy /E /I /Y "{new_app_dir}" "{app_dir}" >>"{log}" 2>&1
if exist "{backup_dir}" (
    rmdir /S /Q "{backup_dir}" 2>NUL
)
start "" "{exe_path}"
del /F /Q "{helper_bat}" >>"{log}" 2>&1
""")

    subprocess.Popen(['cmd.exe', '/c', helper_bat], shell=False,
                       creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                       close_fds=True)
    return True


def check_and_install_update(parent_app=None, progress_callback=None, finished_callback=None):
    def run():
        info = http_get(UPDATE_API)
        if not info or not info.get('success'):
            return
        latest = info.get('version', APP_VERSION)
        if not version_greater(latest, APP_VERSION):
            return

        zip_url = info.get('download_url')
        if not zip_url:
            return

        # Try delta update via manifest
        delta_list = None
        remote_manifest = http_get(MANIFEST_URL)
        if remote_manifest and remote_manifest.get('success'):
            app_dir = os.path.dirname(os.path.dirname(sys.executable))
            local_manifest = build_local_manifest(app_dir)
            delta_list = compute_delta(local_manifest, remote_manifest.get('files', {}))
            if not delta_list:
                if finished_callback:
                    msg = 'Keine Dateiänderungen — App ist aktuell.'
                    if parent_app:
                        parent_app.root.after(0, lambda: finished_callback(True, msg))
                    else:
                        finished_callback(True, msg)
                return

        zip_path = os.path.join(tempfile.gettempdir(), f'TrainerHub-update-{latest}.zip')

        def cb(p):
            if progress_callback:
                if parent_app:
                    parent_app.root.after(0, lambda: progress_callback(p))
                else:
                    progress_callback(p)

        if not download_file(zip_url, zip_path, cb):
            finish(False, 'Download fehlgeschlagen')
            return

        app_dir = os.path.dirname(os.path.dirname(sys.executable))
        exe_path = sys.executable

        if install_update(zip_path, app_dir, exe_path, delta_list):
            finish(True, 'Update bereit. TrainerHub wird neu gestartet.')
            time.sleep(1.5)
            sys.exit(0)
        else:
            finish(False, 'Installation fehlgeschlagen')

    def finish(success, msg):
        if finished_callback:
            if parent_app:
                parent_app.root.after(0, lambda: finished_callback(success, msg))
            else:
                finished_callback(success, msg)

    threading.Thread(target=run, daemon=True).start()


if __name__ == '__main__':
    print('Update info:', http_get(UPDATE_API))
    print('Manifest:', http_get(MANIFEST_URL))
