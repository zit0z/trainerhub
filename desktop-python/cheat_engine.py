"""SweetCheat Cheat Engine — real memory + savegame + process cheat runtime."""
import os
import re
import sys
import json
import time
import shutil
import struct
import threading
import subprocess
from pathlib import Path

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

IS_WINDOWS = sys.platform.startswith('win')

if IS_WINDOWS:
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        HAS_WIN32 = True
    except Exception:
        HAS_WIN32 = False
else:
    HAS_WIN32 = False


class CheatEngine:
    """Find running game processes, scan memory, patch savegames and run console commands."""

    def __init__(self, logger=None):
        self.log = logger or print
        self._handles = {}  # pid -> (handle, game_info)

    # -------------------- PROCESS / MEMORY --------------------

    def find_game_process(self, game_info):
        """Find PID by executable names or window titles."""
        if not HAS_PSUTIL:
            return None
        exes = [e.lower() for e in game_info.get('executables', [])]
        windows = [w.lower() for w in game_info.get('window_titles', [])]
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
            try:
                name = (proc.info['name'] or '').lower()
                exe = (proc.info['exe'] or '').lower()
                if any(e in name or e in exe for e in exes):
                    return proc.info['pid']
                cmd = ' '.join(proc.info['cmdline'] or []).lower()
                if any(e in cmd for e in exes):
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        # Fallback: window title scan on Windows
        if IS_WINDOWS and HAS_WIN32:
            for title in windows:
                hwnd = ctypes.windll.user32.FindWindowW(None, title)
                if not hwnd:
                    continue
                pid = wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value:
                    return pid.value
        return None

    def is_game_running(self, game_info):
        return self.find_game_process(game_info) is not None

    def read_memory(self, pid, address, size):
        if not HAS_WIN32:
            return None
        handle = self._get_handle(pid)
        if not handle:
            return None
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t(0)
        ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(address), buf, size, ctypes.byref(read))
        if not ok or read.value != size:
            return None
        return buf.raw

    def write_memory(self, pid, address, data):
        if not HAS_WIN32:
            return False
        handle = self._get_handle(pid)
        if not handle:
            return False
        written = ctypes.c_size_t(0)
        buf = ctypes.create_string_buffer(data)
        return bool(kernel32.WriteProcessMemory(handle, ctypes.c_void_p(address), buf, len(data), ctypes.byref(written)))

    def _get_handle(self, pid):
        if pid in self._handles:
            return self._handles[pid]
        if not HAS_WIN32:
            return None
        PROCESS_ALL_ACCESS = 0x1F0FFF
        handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not handle:
            return None
        self._handles[pid] = handle
        return handle

    def _scan_region(self, handle, base, size, pattern, value_type='int32'):
        """Naive byte scan over a memory region. Returns first match address."""
        CHUNK = 65536
        for offset in range(0, size, CHUNK):
            to_read = min(CHUNK, size - offset)
            buf = ctypes.create_string_buffer(to_read)
            read = ctypes.c_size_t(0)
            ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(base + offset), buf, to_read, ctypes.byref(read))
            if not ok:
                continue
            data = buf.raw[:read.value]
            try:
                if value_type == 'int32':
                    fmt = 'i'
                    step = 4
                elif value_type == 'int64':
                    fmt = 'q'
                    step = 8
                elif value_type == 'float':
                    fmt = 'f'
                    step = 4
                elif value_type == 'double':
                    fmt = 'd'
                    step = 8
                else:
                    fmt = 'i'
                    step = 4
                for i in range(0, len(data) - step + 1, step):
                    if struct.unpack_from(fmt, data, i)[0] == pattern:
                        return base + offset + i
            except Exception:
                continue
        return None

    def find_value_address(self, pid, value, value_type='int32'):
        if not HAS_WIN32 or not HAS_PSUTIL:
            return None
        handle = self._get_handle(pid)
        if not handle:
            return None
        proc = psutil.Process(pid)
        for m in proc.memory_maps(grouped=False):
            try:
                # Only scan writable private regions (heap/stack/mapped data)
                if 'Private' not in m.path and 'Heap' not in m.path and 'Stack' not in m.path:
                    continue
                base = int(m.addr.split('-')[0], 16)
                size = m.rss
                if size < 4096:
                    continue
                addr = self._scan_region(handle, base, size, value, value_type)
                if addr:
                    return addr
            except Exception:
                continue
        return None

    # -------------------- SAVEGAME PARSING --------------------

    def locate_savegame(self, game_info):
        """Locate newest savegame file/directory."""
        candidates = []
        for folder in game_info.get('savegame_folders', []):
            folder = os.path.expandvars(folder)
            if os.path.isdir(folder):
                candidates.append(folder)
        for path in game_info.get('savegame_paths', []):
            path = os.path.expandvars(path)
            if os.path.exists(path):
                candidates.append(path)
        if not candidates:
            return None
        newest = None
        newest_time = 0
        for c in candidates:
            try:
                if os.path.isdir(c):
                    # find newest file inside
                    for root, _, files in os.walk(c):
                        for f in files:
                            fp = os.path.join(root, f)
                            try:
                                mt = os.path.getmtime(fp)
                                if mt > newest_time:
                                    newest_time = mt
                                    newest = fp
                            except Exception:
                                continue
                else:
                    mt = os.path.getmtime(c)
                    if mt > newest_time:
                        newest_time = mt
                        newest = c
            except Exception:
                continue
        return newest

    def backup_savegame(self, savegame_path, backup_dir=None):
        if not savegame_path or not os.path.exists(savegame_path):
            return None
        if not backup_dir:
            backup_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'SweetCheat-Backups')
        os.makedirs(backup_dir, exist_ok=True)
        ts = time.strftime('%Y%m%d-%H%M%S')
        base = os.path.basename(savegame_path)
        backup_path = os.path.join(backup_dir, f"{base}-{ts}.backup")
        try:
            if os.path.isdir(savegame_path):
                shutil.make_archive(backup_path, 'zip', savegame_path)
            else:
                shutil.copy2(savegame_path, backup_path)
            return backup_path
        except Exception as e:
            self.log(f'Backup failed: {e}')
            return None

    def edit_json_savegame(self, savegame_path, field, value):
        if not savegame_path or not os.path.exists(savegame_path):
            return False, 'Savegame nicht gefunden'
        try:
            with open(savegame_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Simple dotted path: money or player.money
            parts = field.split('.')
            cur = data
            for p in parts[:-1]:
                cur = cur.setdefault(p, {})
            cur[parts[-1]] = value
            with open(savegame_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True, f'{field} = {value}'
        except Exception as e:
            return False, f'JSON-Edit fehlgeschlagen: {e}'

    def edit_xml_savegame(self, savegame_path, tag, value):
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(savegame_path)
            root = tree.getroot()
            found = False
            for el in root.iter(tag):
                el.text = str(value)
                found = True
            if not found:
                return False, f'Tag <{tag}> nicht gefunden'
            tree.write(savegame_path, encoding='utf-8', xml_declaration=True)
            return True, f'<{tag}> = {value}'
        except Exception as e:
            return False, f'XML-Edit fehlgeschlagen: {e}'

    # -------------------- CONSOLE / COMMANDS --------------------

    def run_console_command(self, command, game_info=None):
        """For games with developer console, send command via keyboard injection (Windows only)."""
        if not IS_WINDOWS or not HAS_WIN32:
            return False, 'Konsole nur auf Windows verfügbar'
        pid = self.find_game_process(game_info) if game_info else None
        if game_info and not pid:
            return False, 'Spielprozess nicht gefunden'
        # Simple PostMessage to active window
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if game_info:
            title = (game_info.get('window_titles') or [''])[0]
            hwnd = ctypes.windll.user32.FindWindowW(None, title) or hwnd
        # Open console with tilde, type command, press enter
        # This is best-effort; many games block synthetic input.
        try:
            import pyautogui
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(0.1)
            pyautogui.keyDown('tilde')
            pyautogui.keyUp('tilde')
            time.sleep(0.1)
            pyautogui.typewrite(command, interval=0.01)
            pyautogui.keyDown('return')
            pyautogui.keyUp('return')
            return True, f'Konsolenbefehl gesendet: {command}'
        except Exception as e:
            return False, f'Konsole konnte nicht bedient werden: {e}'

    # -------------------- HIGH-LEVEL ACTIVATE --------------------

    def can_activate(self, trainer, game_info=None):
        if not game_info:
            game_info = trainer.get('game', {})
        method = trainer.get('method', 'savegame')
        if method == 'memory':
            if not IS_WINDOWS:
                return False, 'Memory-Cheats erfordern Windows'
            if not HAS_PSUTIL:
                return False, 'psutil fehlt'
            if not HAS_WIN32:
                return False, 'Windows-API nicht verfügbar'
            pid = self.find_game_process(game_info)
            if not pid:
                return False, f"Starte zuerst: {game_info.get('name','das Spiel')}"
        elif method == 'console':
            if not IS_WINDOWS:
                return False, 'Konsole nur auf Windows'
            pid = self.find_game_process(game_info)
            if not pid:
                return False, f"Spiel muss laufen: {game_info.get('name','das Spiel')}"
        elif method in ('savegame', 'savegame_edit'):
            save = self.locate_savegame(game_info)
            if not save:
                return False, 'Savegame nicht gefunden. Speicher einmal im Spiel.'
        else:
            return False, f'Unbekannte Methode: {method}'
        return True, None

    def activate(self, trainer, game_info=None, callback=None):
        if game_info is None:
            game_info = trainer.get('game', {})
        method = trainer.get('method', 'savegame')
        success = False
        message = 'Unbekannter Fehler'
        try:
            if method == 'memory':
                success, message = self._do_memory_cheat(trainer, game_info)
            elif method == 'console':
                success, message = self.run_console_command(trainer.get('command',''), game_info)
            elif method in ('savegame', 'savegame_edit'):
                success, message = self._do_savegame_cheat(trainer, game_info)
            else:
                message = f'Methode {method} nicht unterstützt'
        except Exception as e:
            success = False
            message = f'Fehler: {e}'
        if callback:
            callback(success, message)
        return success, message

    def _do_memory_cheat(self, trainer, game_info):
        pid = self.find_game_process(game_info)
        if not pid:
            return False, 'Spielprozess nicht gefunden'
        value = trainer.get('scan_value')
        value_type = trainer.get('value_type', 'int32')
        new_value = trainer.get('set_value')
        field = trainer.get('field')
        if value is None and field:
            # Static address path, e.g. base+offset
            value = field
        if value is None:
            return False, 'Kein Scan-Wert definiert'
        addr = self.find_value_address(pid, value, value_type)
        if not addr:
            return False, f'Wert {value} nicht im Speicher gefunden. Öffne das Savegame und checke den aktuellen Wert.'
        if new_value is None:
            return False, 'Kein neuer Wert definiert'
        fmt = {'int32':'i','int64':'q','float':'f','double':'d'}.get(value_type, 'i')
        data = struct.pack(fmt, new_value)
        ok = self.write_memory(pid, addr, data)
        if ok:
            return True, f'{trainer.get("name")} aktiviert (0x{addr:X})'
        return False, 'Speicher konnte nicht geschrieben werden (Zugriff verweigert)'

    def _do_savegame_cheat(self, trainer, game_info):
        save = self.locate_savegame(game_info)
        if not save:
            return False, 'Savegame nicht gefunden'
        backup = self.backup_savegame(save)
        field = trainer.get('field')
        value = trainer.get('set_value')
        tag = trainer.get('xml_tag')
        if not field and not tag:
            return False, 'Kein Savegame-Feld definiert'
        if tag:
            ok, msg = self.edit_xml_savegame(save, tag, value)
        else:
            ok, msg = self.edit_json_savegame(save, field, value)
        if ok and backup:
            msg += f' (Backup: {os.path.basename(backup)})'
        return ok, msg
