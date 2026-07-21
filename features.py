"""Additional TrainerHub features: hotkeys, launcher, history, config sync."""
import json
import os
import time
import urllib.request
import urllib.error
import threading
from tkinter import messagebox, simpledialog

try:
    import win32api
    import win32con
    import win32gui
    WINDOWS = True
except ImportError:
    WINDOWS = False


class HotkeyManager:
    """Global hotkey manager for Windows."""
    def __init__(self, log_callback=None):
        self.log = log_callback or print
        self.hotkeys = {}
        self._running = False
        self._thread = None

    def register(self, key_combo, callback, name=''):
        if not WINDOWS:
            self.log("Hotkeys nur auf Windows verfügbar.")
            return False
        self.hotkeys[key_combo.lower()] = {'callback': callback, 'name': name}
        return True

    def start(self):
        if not WINDOWS or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        # Simplified polling hotkey detection using GetAsyncKeyState
        state = {}
        key_map = {
            'f1': win32con.VK_F1, 'f2': win32con.VK_F2, 'f3': win32con.VK_F3,
            'f4': win32con.VK_F4, 'f5': win32con.VK_F5, 'f6': win32con.VK_F6,
            'f7': win32con.VK_F7, 'f8': win32con.VK_F8, 'f9': win32con.VK_F9,
            'f10': win32con.VK_F10, 'f11': win32con.VK_F11, 'f12': win32con.VK_F12,
        }
        while self._running:
            time.sleep(0.1)
            for combo, info in list(self.hotkeys.items()):
                keys = combo.split('+')
                vk = key_map.get(keys[-1].lower())
                if not vk:
                    continue
                ctrl = 'ctrl' in keys
                alt = 'alt' in keys
                shift = 'shift' in keys
                pressed = win32api.GetAsyncKeyState(vk) < 0
                if ctrl and not (win32api.GetAsyncKeyState(win32con.VK_CONTROL) < 0):
                    continue
                if alt and not (win32api.GetAsyncKeyState(win32con.VK_MENU) < 0):
                    continue
                if shift and not (win32api.GetAsyncKeyState(win32con.VK_SHIFT) < 0):
                    continue
                if pressed:
                    if not state.get(combo, False):
                        state[combo] = True
                        try:
                            info['callback']()
                        except Exception as e:
                            self.log(f"Hotkey {combo} Fehler: {e}")
                else:
                    state[combo] = False

    def stop(self):
        self._running = False


class GameLauncher:
    """Detect and launch common game platforms/executables."""
    COMMON_PATHS = [
        os.path.expandvars('%PROGRAMFILES(x86)%\\Steam\\steam.exe'),
        os.path.expandvars('%PROGRAMFILES%\\Steam\\steam.exe'),
        os.path.expandvars('%LOCALAPPDATA%\\EpicGamesLauncher\\Saved\\Logs'),
    ]

    def __init__(self, log_callback=None):
        self.log = log_callback or print

    def find_game_exe(self, exe_name):
        """Search common locations for game exe."""
        search_roots = [
            os.path.expandvars('%PROGRAMFILES(x86)%'),
            os.path.expandvars('%PROGRAMFILES%'),
            os.path.expandvars('%LOCALAPPDATA%'),
            os.path.expandvars('%USERPROFILE%\\Documents\\My Games'),
        ]
        for root in search_roots:
            if not os.path.exists(root):
                continue
            for dirpath, _, filenames in os.walk(root):
                if exe_name.lower() in [f.lower() for f in filenames]:
                    return os.path.join(dirpath, exe_name)
                if len(dirpath) > len(root) + 120:  # Limit depth
                    break
        return None

    def launch(self, exe_path):
        if not WINDOWS:
            self.log("Spielstart nur auf Windows.")
            return False
        try:
            import subprocess
            subprocess.Popen(exe_path, shell=False)
            self.log(f"Spiel gestartet: {exe_path}")
            return True
        except Exception as e:
            self.log(f"Start fehlgeschlagen: {e}")
            return False


class ConfigSync:
    """Sync user config and favorites with the TrainerHub API."""
    def __init__(self, api_base, api_key, log_callback=None):
        self.api_base = api_base
        self.api_key = api_key
        self.log = log_callback or print

    def api_call(self, endpoint, method='GET', data=None):
        headers = {'User-Agent': 'TrainerHub-Desktop/0.4.1'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        url = f'{self.api_base}/{endpoint}'
        try:
            if method == 'GET':
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.loads(r.read().decode('utf-8'))
            else:
                body = json.dumps(data).encode('utf-8') if data else b''
                req = urllib.request.Request(url, data=body,
                                             headers={**headers, 'Content-Type': 'application/json'},
                                             method='POST')
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def upload_favorites(self, favorites):
        return self.api_call('config-sync.php?action=upload', 'POST', {
            'type': 'favorites',
            'data': list(favorites)
        })

    def download_favorites(self):
        return self.api_call('config-sync.php?action=download', 'POST', {'type': 'favorites'})

    def log_history(self, trainer_name, game_slug, success=True):
        return self.api_call('trainer-logs.php', 'POST', {
            'game_slug': game_slug,
            'trainer_name': trainer_name,
            'success': success
        })


class UpdateNotifier:
    """Check for updates and notify user."""
    def __init__(self, current_version, api_base, log_callback=None):
        self.current_version = current_version
        self.api_base = api_base
        self.log = log_callback or print

    def check(self):
        try:
            req = urllib.request.Request(f'{self.api_base}/version.php', headers={'User-Agent': 'TrainerHub-Desktop'})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode('utf-8'))
            if data.get('success') and data.get('version') != self.current_version:
                return data.get('version'), data.get('download_url')
        except Exception as e:
            self.log(f"Update-Check fehlgeschlagen: {e}")
        return None, None


class ThemeManager:
    """Manage UI themes."""
    THEMES = {
        'dark': {
            'bg': '#050507', 'card': '#111118', 'input': '#0a0a10', 'border': '#232333',
            'text': '#f8fafc', 'muted': '#94a3b8', 'accent': '#2563eb'
        },
        'midnight': {
            'bg': '#0f172a', 'card': '#1e293b', 'input': '#334155', 'border': '#475569',
            'text': '#f1f5f9', 'muted': '#cbd5e1', 'accent': '#8b5cf6'
        },
        'neon': {
            'bg': '#000000', 'card': '#111111', 'input': '#1a1a1a', 'border': '#00ff9d',
            'text': '#ffffff', 'muted': '#a3a3a3', 'accent': '#00ff9d'
        }
    }

    def __init__(self, config_file=None):
        self.config_file = config_file
        self.current = 'dark'

    def get(self, name):
        return self.THEMES.get(name, self.THEMES['dark'])

    def apply(self, name):
        self.current = name
        # Applied at runtime by GUI
        return self.get(name)
