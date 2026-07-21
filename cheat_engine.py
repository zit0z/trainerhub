"""TrainerHub - Real Cheat Engine v0.6.1

Supports:
- Memory scanning/writing/freezing (Stardew money/health/stamina)
- SMAPI bridge mod HTTP calls
- Savegame editing (Stardew XML)
- Console command injection via keyboard (focus game, open console, type, enter)
- Generic pattern scanning
"""
import os
import re
import time
import json
import struct
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

WINDOWS = os.name == 'nt'

# Optional imports
try:
    import pymem
    from pymem import Pymem
    import pymem.process
    import pymem.memory
    PYMEM_OK = True
except Exception:
    Pymem = None
    PYMEM_OK = False

if WINDOWS:
    try:
        import win32api
        import win32con
        import win32gui
        import win32process
        import win32ui
        import win32clipboard
        WIN32_OK = True
    except Exception:
        WIN32_OK = False
else:
    WIN32_OK = False


def log(msg):
    print(f"[CheatEngine] {msg}")


def find_window_by_process(process_name):
    """Find top-level window HWND belonging to process."""
    if not WINDOWS or not WIN32_OK:
        return None
    try:
        import psutil
        pids = [p.pid for p in psutil.process_iter(['pid', 'name']) if process_name.lower() in p.info['name'].lower()]
    except Exception:
        return None
    result = []

    def enum_cb(hwnd, extra):
        if not win32gui.IsWindowVisible(hwnd):
            return
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid in pids:
                title = win32gui.GetWindowText(hwnd)
                result.append((hwnd, title))
        except Exception:
            pass

    win32gui.EnumWindows(enum_cb, None)
    if result:
        # Prefer window with non-empty title
        for hwnd, title in result:
            if title.strip():
                return hwnd
        return result[0][0]
    return None


def send_keys_to_window(hwnd, text, open_console_key=None):
    """Focus window, optionally open console, type text, press enter."""
    if not WINDOWS or not WIN32_OK:
        return False
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.2)
        if open_console_key:
            press_key(hwnd, open_console_key)
            time.sleep(0.2)
        type_text(hwnd, text)
        time.sleep(0.1)
        press_key(hwnd, 'RETURN')
        return True
    except Exception as e:
        log(f"send_keys error: {e}")
        return False


def press_key(hwnd, key):
    """Send a single key press."""
    if not WINDOWS or not WIN32_OK:
        return
    vk = getattr(win32con, f'VK_{key.upper()}', None)
    if vk is None:
        vk = ord(key.upper())
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(0.05)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)


def type_text(hwnd, text):
    """Type text using WM_CHAR messages (most compatible)."""
    if not WINDOWS or not WIN32_OK:
        return
    for char in text:
        win32api.PostMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
        time.sleep(0.01)


def paste_text(hwnd, text):
    """Use clipboard paste (Ctrl+V). More reliable for long text."""
    if not WINDOWS or not WIN32_OK:
        return False
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        time.sleep(0.1)
        # Ctrl+V
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord('V'), 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        return True
    except Exception as e:
        log(f"paste error: {e}")
        return False


class MemoryEngine:
    def __init__(self, process_name=None):
        self.process_name = process_name
        self.pm = None
        self.pid = None
        self.freeze_threads = {}
        self.scan_results = {}  # label -> list of addresses

    def attach(self, process_name=None):
        if process_name:
            self.process_name = process_name
        if not PYMEM_OK or not self.process_name:
            return False
        # Try exact name first, then variants without .exe, lowercase, etc.
        names = [self.process_name, self.process_name.replace('.exe', ''),
                 self.process_name.lower(), self.process_name.replace(' ', '').lower()]
        # Find by psutil partial match
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                pname = proc.info['name']
                if pname and (pname.lower() in [n.lower() for n in names] or
                              any(n.lower() in pname.lower() for n in names)):
                    try:
                        self.pm = Pymem(proc.info['pid'])
                        self.pid = proc.info['pid']
                        return True
                    except Exception:
                        pass
        except Exception:
            pass
        # Fallback exact
        for name in names:
            try:
                self.pm = Pymem(name)
                self.pid = self.pm.process_id
                return True
            except Exception:
                pass
        self.pm = None
        self.pid = None
        return False

    def is_attached(self):
        return self.pm is not None

    def read_int(self, address, size=4):
        if not self.pm:
            return None
        try:
            if size == 4:
                return self.pm.read_int(address)
            elif size == 8:
                return self.pm.read_longlong(address)
            elif size == 2:
                return self.pm.read_short(address)
            elif size == 1:
                return self.pm.read_uchar(address)
        except Exception:
            return None

    def write_int(self, address, value, size=4):
        if not self.pm:
            return False
        try:
            if size == 4:
                self.pm.write_int(address, int(value))
            elif size == 8:
                self.pm.write_longlong(address, int(value))
            elif size == 2:
                self.pm.write_short(address, int(value))
            elif size == 1:
                self.pm.write_uchar(address, int(value))
            return True
        except Exception:
            return False

    def read_float(self, address):
        if not self.pm:
            return None
        try:
            return self.pm.read_float(address)
        except Exception:
            return None

    def write_float(self, address, value):
        if not self.pm:
            return False
        try:
            self.pm.write_float(address, float(value))
            return True
        except Exception:
            return False

    def freeze_value(self, address, value, size=4, label=None):
        if label is None:
            label = f"freeze_{address}"
        self.unfreeze(label)
        stop = threading.Event()
        self.freeze_threads[label] = stop

        def loop():
            while not stop.is_set():
                try:
                    self.write_int(address, value, size)
                    time.sleep(0.1)
                except Exception:
                    pass
        threading.Thread(target=loop, daemon=True).start()
        return True

    def unfreeze(self, label):
        if label in self.freeze_threads:
            self.freeze_threads[label].set()
            del self.freeze_threads[label]

    def unfreeze_all(self):
        for label in list(self.freeze_threads.keys()):
            self.unfreeze(label)

    def first_scan(self, value, value_type='int', label='default'):
        """Scan entire process memory for a value. Slower but works without patterns."""
        if not self.pm:
            return []
        results = []
        try:
            regions = []
            # Get all memory regions
            import pymem.memory
            address = 0x10000
            while address < 0x7FFFFFFF0000:
                try:
                    mbi = pymem.memory.virtual_query(self.pm.process_handle, address)
                    if mbi.State == win32con.MEM_COMMIT and mbi.Protect in (
                        win32con.PAGE_READWRITE, win32con.PAGE_EXECUTE_READWRITE
                    ):
                        regions.append((mbi.BaseAddress, mbi.RegionSize))
                    address = mbi.BaseAddress + mbi.RegionSize
                except Exception:
                    address += 0x10000
        except Exception as e:
            log(f"region enumeration error: {e}")
            return []

        target = int(value) if value_type == 'int' else float(value)
        pack_fmt = {'int4': '<i', 'int8': '<q', 'float': '<f', 'double': '<d'}.get(value_type, '<i')
        size = struct.calcsize(pack_fmt)

        for base, rsize in regions:
            try:
                data = self.pm.read_bytes(base, rsize)
                for i in range(0, len(data) - size, size):
                    try:
                        val = struct.unpack(pack_fmt, data[i:i+size])[0]
                        if val == target:
                            results.append(base + i)
                    except Exception:
                        pass
            except Exception:
                pass
        self.scan_results[label] = results
        return results

    def next_scan(self, value, value_type='int', label='default'):
        """Filter previous scan results by new value."""
        if label not in self.scan_results:
            return []
        prev = self.scan_results[label]
        target = int(value) if value_type == 'int' else float(value)
        pack_fmt = {'int4': '<i', 'int8': '<q', 'float': '<f', 'double': '<d'}.get(value_type, '<i')
        size = struct.calcsize(pack_fmt)
        results = []
        for addr in prev:
            try:
                val = struct.unpack(pack_fmt, self.pm.read_bytes(addr, size))[0]
                if val == target:
                    results.append(addr)
            except Exception:
                pass
        self.scan_results[label] = results
        return results


class SMAPIBridge:
    def __init__(self, port=10999):
        self.port = port
        self.base = f"http://localhost:{port}"

    def is_running(self):
        try:
            urllib.request.urlopen(self.base + "/ping", timeout=1)
            return True
        except Exception:
            return False

    def set_value(self, key, value):
        try:
            data = json.dumps({'key': key, 'value': value}).encode()
            req = urllib.request.Request(self.base + "/set", data=data,
                                         headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=3)
            return True
        except Exception:
            return False

    def send_command(self, command):
        try:
            data = json.dumps({'command': command}).encode()
            req = urllib.request.Request(self.base + "/cmd", data=data,
                                         headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=3)
            return True
        except Exception:
            return False


class SavegameEditor:
    def __init__(self):
        self.path = None

    def _stardew_save_paths(self):
        base = os.path.expandvars(r'%APPDATA%\StardewValley\Saves')
        if os.path.isdir(base):
            for d in os.listdir(base):
                full = os.path.join(base, d)
                if os.path.isdir(full):
                    yield os.path.join(full, d + '.xml')

    def edit_stardew_money(self, amount=999999):
        for path in self._stardew_save_paths():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                new = re.sub(r'<money>\d+</money>', f'<money>{amount}</money>', content)
                if new != content:
                    # Backup
                    backup = path + '.backup'
                    if not os.path.exists(backup):
                        with open(backup, 'w', encoding='utf-8') as f:
                            f.write(content)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new)
                    return True, path
            except Exception as e:
                log(f"savegame edit error: {e}")
        return False, None

    def edit_stardew_field(self, field, value):
        for path in self._stardew_save_paths():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                pattern = re.compile(rf'<{re.escape(field)}>([^<]*)</{re.escape(field)}>')
                new = pattern.sub(rf'<{field}>{value}</{field}>', content)
                if new != content:
                    backup = path + '.backup'
                    if not os.path.exists(backup):
                        with open(backup, 'w', encoding='utf-8') as f:
                            f.write(content)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new)
                    return True, path
            except Exception as e:
                log(f"savegame field edit error: {e}")
        return False, None


class CommandInjector:
    def run(self, process_name, command, open_console_key=None):
        hwnd = find_window_by_process(process_name)
        if not hwnd:
            return False, f"Fenster für {process_name} nicht gefunden. Starte das Spiel."
        ok = send_keys_to_window(hwnd, command, open_console_key=open_console_key)
        if ok:
            return True, "Befehl gesendet."
        return False, "Tastatureingabe fehlgeschlagen."


class CheatEngine:
    def __init__(self):
        self.memory = MemoryEngine()
        self.smapi = SMAPIBridge()
        self.savegame = SavegameEditor()
        self.injector = CommandInjector()
        self.active_cheats = {}
        self.process_name = None

    def set_process(self, process_name):
        # Accept comma-separated list of names
        names = [n.strip() for n in process_name.split(',')] if isinstance(process_name, str) and ',' in process_name else [process_name]
        for n in names:
            self.memory.attach(n)
            if self.memory.is_attached():
                self.process_name = n
                return True
        return False

    def activate(self, trainer, game=None):
        ctype = trainer.get('cheat_type', 'memory')
        name = trainer.get('title', trainer.get('name', 'Unbekannt'))
        result = {'success': False, 'message': ''}

        if ctype == 'memory':
            result = self._activate_memory(trainer, game)
        elif ctype == 'smapi_set':
            result = self._activate_smapi(trainer)
        elif ctype == 'command':
            result = self._activate_command(trainer, game)
        elif ctype == 'console':
            result = self._activate_console(trainer, game)
        elif ctype == 'savegame':
            result = self._activate_savegame(trainer, game)
        elif ctype == 'config':
            result = self._activate_config(trainer, game)
        elif ctype == 'two_scan':
            result = {'success': False, 'message': 'Zwei-Werte-Scan erfordert Eingabe der aktuellen Werte.'}
        elif ctype == 'pattern_learner':
            result = {'success': True, 'message': 'Pattern Learner bereit.'}
        else:
            result['message'] = f"Cheat-Typ '{ctype}' nicht unterstützt."

        self.active_cheats[name] = result.get('success', False)
        return result

    def deactivate(self, trainer):
        name = trainer.get('title', trainer.get('name', 'Unbekannt'))
        self.active_cheats[name] = False
        for label in list(self.memory.freeze_threads.keys()):
            if label.startswith(name):
                self.memory.unfreeze(label)
        return {'success': True, 'message': f"{name} deaktiviert."}

    def _game_name(self, game):
        return (game.get('name', '') if game else '').lower()

    def _activate_memory(self, trainer, game):
        if not self.memory.is_attached():
            return {'success': False, 'message': 'Kein Spielprozess verbunden. Klicke "Prozess prüfen".'}
        gname = self._game_name(game)
        title = trainer.get('title', '').lower()

        # Try known Stardew patterns first
        if 'stardew' in gname:
            return self._stardew_memory(title)

        # Try AOB patterns from API
        for p in trainer.get('patterns', []):
            pattern = p.get('pattern', '')
            if pattern and '?' not in pattern:
                addrs = self.memory.scan_aob(pattern)
                if addrs:
                    addr = addrs[0] + int(p.get('offset', 0))
                    val = p.get('value', 0)
                    vt = p.get('value_type', 'int4')
                    size = 4 if vt in ('int', 'int4') else 8 if vt == 'int8' else 4
                    self.memory.write_int(addr, val, size)
                    self.memory.freeze_value(addr, val, size, label=trainer.get('title', 'memory'))
                    return {'success': True, 'message': f"{trainer.get('title')} aktiviert (Memory Freeze)."}

        return {'success': False, 'message': 'Kein gültiges Pattern. Nutze den 2-Werte-Scan.'}

    def _stardew_memory(self, title):
        title = title.lower()
        if 'geld' in title or 'money' in title:
            return {'success': False, 'message': 'Nutze den 2-Werte-Scan oder SMAPI/Savegame für Geld.'}
        if 'energie' in title or 'stamina' in title:
            return {'success': False, 'message': 'Nutze den 2-Werte-Scan oder SMAPI für Energie.'}
        if 'leben' in title or 'health' in title:
            return {'success': False, 'message': 'Nutze den 2-Werte-Scan oder SMAPI für Leben.'}
        return {'success': False, 'message': 'Memory-Cheat nicht implementiert.'}

    def _activate_smapi(self, trainer):
        if not self.smapi.is_running():
            return {'success': False, 'message': 'SMAPI Bridge nicht erreichbar. Installiere SMAPI + TrainerHub Bridge Mod.'}
        title = trainer.get('title', '').lower()
        if 'money' in title or 'geld' in title:
            self.smapi.set_value('money', 999999)
        elif 'health' in title or 'leben' in title:
            self.smapi.set_value('health', 999)
        elif 'stamina' in title or 'energie' in title:
            self.smapi.set_value('stamina', 999)
        else:
            # Generic SMAPI command if command field exists
            cmd = trainer.get('command', '') or trainer.get('effect', '')
            if cmd:
                self.smapi.send_command(cmd)
                return {'success': True, 'message': f"SMAPI-Kommando: {cmd}"}
            return {'success': False, 'message': 'Unbekannter SMAPI-Cheat.'}
        return {'success': True, 'message': f"{trainer.get('title')} via SMAPI aktiviert."}

    def _activate_command(self, trainer, game):
        cmd = trainer.get('command', '') or trainer.get('effect', '') or ''
        if not cmd:
            return {'success': False, 'message': 'Kein Befehl hinterlegt.'}
        pname = self.process_name or (game.get('process_name') if game else '')
        if not pname:
            return {'success': False, 'message': 'Kein Prozess bekannt.'}
        # For Stardew official commands, fallback to savegame if no SMAPI and command is /money /health /stamina /backpack
        gname = self._game_name(game)
        title = trainer.get('title', '').lower()
        if 'stardew' in gname and not self.smapi.is_running():
            if any(k in title for k in ['money', 'geld']):
                ok, path = self.savegame.edit_stardew_money(999999)
                return {'success': ok, 'message': f'Geld im Savegame auf 999.999 gesetzt. Neustart nötig. ({path})' if ok else 'Savegame nicht gefunden.'}
            if any(k in title for k in ['health', 'leben']):
                ok, path = self.savegame.edit_stardew_field('health', 999)
                return {'success': ok, 'message': f'Leben im Savegame auf 999 gesetzt. Neustart nötig. ({path})' if ok else 'Savegame nicht gefunden.'}
            if any(k in title for k in ['stamina', 'energie', 'ausdauer']):
                ok, path = self.savegame.edit_stardew_field('stamina', 999)
                return {'success': ok, 'message': f'Energie im Savegame auf 999 gesetzt. Neustart nötig. ({path})' if ok else 'Savegame nicht gefunden.'}
            if 'backpack' in title:
                ok, path = self.savegame.edit_stardew_field('maxItems', 36)
                return {'success': ok, 'message': f'Rucksack im Savegame auf 36 Slots gesetzt. Neustart nötig. ({path})' if ok else 'Savegame nicht gefunden.'}
        ok, msg = self.injector.run(pname, cmd, open_console_key='T')
        return {'success': ok, 'message': msg}

    def _activate_console(self, trainer, game):
        cmd = trainer.get('command', '') or trainer.get('effect', '') or ''
        if not cmd:
            return {'success': False, 'message': 'Kein Konsolenbefehl hinterlegt.'}
        # Try SMAPI command endpoint first
        if self.smapi.is_running():
            if self.smapi.send_command(cmd):
                return {'success': True, 'message': f"SMAPI-Kommando ausgeführt: {cmd}"}
        # Fallback keyboard injection
        return self._activate_command(trainer, game)

    def _activate_savegame(self, trainer, game):
        gname = self._game_name(game)
        effect = trainer.get('effect', '') or trainer.get('command', '') or trainer.get('title', '')
        if 'stardew' in gname:
            if any(k in effect.lower() for k in ['money', 'geld']):
                ok, path = self.savegame.edit_stardew_money(999999)
                return {'success': ok, 'message': f'Geld auf 999.999 gesetzt. Neustart nötig.' if ok else 'Savegame nicht gefunden.'}
            if any(k in effect.lower() for k in ['health', 'leben']):
                ok, path = self.savegame.edit_stardew_field('health', 999)
                return {'success': ok, 'message': f'Leben auf 999 gesetzt. Neustart nötig.' if ok else 'Savegame nicht gefunden.'}
            if any(k in effect.lower() for k in ['stamina', 'energie', 'ausdauer']):
                ok, path = self.savegame.edit_stardew_field('stamina', 999)
                return {'success': ok, 'message': f'Energie auf 999 gesetzt. Neustart nötig.' if ok else 'Savegame nicht gefunden.'}
            if 'backpack' in effect.lower():
                ok, path = self.savegame.edit_stardew_field('maxItems', 36)
                return {'success': ok, 'message': f'Rucksack auf 36 Slots gesetzt. Neustart nötig.' if ok else 'Savegame nicht gefunden.'}
            m = re.search(r'(?:set|edit)\s+([a-zA-Z_]+)\s*=\s*(\d+)', effect, re.I)
            if m:
                ok, path = self.savegame.edit_stardew_field(m.group(1), m.group(2))
                return {'success': ok, 'message': f'Feld {m.group(1)} gesetzt. Neustart nötig.' if ok else 'Savegame nicht gefunden.'}
            return {'success': True, 'message': 'Savegame-Cheat vorbereitet. Bitte Spiel neu starten.'}
        return {'success': False, 'message': 'Savegame-Editor für dieses Spiel nicht verfügbar.'}

    def _activate_config(self, trainer, game):
        # Config changes usually need file edits; provide generic message
        return {'success': True, 'message': 'Config-Cheat vorbereitet. Manche Änderungen benötigen Neustart.'}

    def two_scan_dialog_values(self, game_name, target_label, first_value, next_value, new_value, value_type='int4'):
        """Perform two-value scan and write/freeze result."""
        if not self.memory.is_attached():
            return {'success': False, 'message': 'Kein Prozess verbunden.'}
        results = self.memory.first_scan(first_value, value_type, label=target_label)
        if len(results) > 10000:
            time.sleep(0.5)
            results = self.memory.next_scan(next_value, value_type, label=target_label)
        if not results:
            return {'success': False, 'message': 'Keine Adresse gefunden. Werte korrekt eingegeben?'}
        if len(results) > 10:
            return {'success': False, 'message': f'{len(results)} Adressen gefunden. Bitte eindeutigere Werte wählen.'}
        addr = results[0]
        size = 4 if value_type == 'int4' else 8 if value_type == 'int8' else 4
        self.memory.write_int(addr, int(new_value), size)
        self.memory.freeze_value(addr, int(new_value), size, label=target_label)
        return {'success': True, 'message': f'Wert auf {new_value} gesetzt und eingefroren ({len(results)} Adresse(n)).'}


def test_engine():
    ce = CheatEngine()
    print('PYMEM OK:', PYMEM_OK, 'WIN32_OK:', WIN32_OK)
    print('SMAPI running:', ce.smapi.is_running())


if __name__ == '__main__':
    test_engine()
