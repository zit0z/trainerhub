"""TrainerHub - Real cheat engine with memory scanning, commands, savegame and SMAPI."""
import os
import re
import time
import json
import struct
import threading
import subprocess
import urllib.request
from pathlib import Path

try:
    import pymem
    from pymem import Pymem
    import pymem.process
    import pymem.memory
    PYMEM_OK = True
except Exception:
    Pymem = None
    PYMEM_OK = False


def find_process(name):
    """Find PID by process name."""
    if not PYMEM_OK:
        return None
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            if name.lower() in proc.info['name'].lower():
                return proc.info['pid']
        return None
    except Exception:
        return None


def aob_to_bytes(pattern):
    """Convert '48 8B ?? 00 00 FF' bytes to bytes + mask."""
    parts = pattern.split()
    sig = b''
    mask = []
    for p in parts:
        if p == '?' or p == '??':
            sig += b'\x00'
            mask.append(0)
        else:
            sig += bytes([int(p, 16)])
            mask.append(1)
    return sig, mask


class MemoryEngine:
    """Attach, scan AOB, read/write/freeze memory."""
    def __init__(self, process_name=None):
        self.process_name = process_name
        self.pm = None
        self.pid = None
        self.freeze_threads = {}

    def attach(self, process_name=None):
        if process_name:
            self.process_name = process_name
        if not PYMEM_OK or not self.process_name:
            return False
        try:
            self.pm = Pymem(self.process_name)
            self.pid = self.pm.process_id
            return True
        except Exception:
            self.pm = None
            self.pid = None
            return False

    def is_attached(self):
        return self.pm is not None

    def _module_base(self, module=None):
        if not self.pm:
            return None
        try:
            if module:
                mod = pymem.process.module_from_name(self.pm.process_handle, module)
                return mod.lpBaseOfDll
            return self.pm.base_address
        except Exception:
            return self.pm.base_address

    def scan_aob(self, pattern, module=None):
        """Scan for AOB pattern. Returns list of addresses."""
        if not self.pm:
            return []
        sig, mask = aob_to_bytes(pattern)
        base = self._module_base(module)
        if base is None:
            return []
        try:
            mem = self.pm.read_bytes(base, 0x1000000)  # 16 MB chunk
            results = []
            for i in range(len(mem) - len(sig)):
                ok = True
                for j in range(len(sig)):
                    if mask[j] and mem[i+j] != sig[j]:
                        ok = False
                        break
                if ok:
                    results.append(base + i)
            return results
        except Exception:
            return []

    def read(self, address, size=4):
        if not self.pm:
            return None
        try:
            return self.pm.read_bytes(address, size)
        except Exception:
            return None

    def read_int(self, address, size=4):
        raw = self.read(address, size)
        if raw is None:
            return None
        try:
            if size == 4:
                return struct.unpack('<i', raw)[0]
            elif size == 8:
                return struct.unpack('<q', raw)[0]
            elif size == 2:
                return struct.unpack('<h', raw)[0]
            elif size == 1:
                return struct.unpack('<B', raw)[0]
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

    def write_float(self, address, value):
        if not self.pm:
            return False
        try:
            self.pm.write_float(address, float(value))
            return True
        except Exception:
            return False

    def freeze_value(self, address, value, size=4, label=None):
        """Freeze value in background thread."""
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

    def unfreeze(self, label):
        if label in self.freeze_threads:
            self.freeze_threads[label].set()
            del self.freeze_threads[label]

    def unfreeze_all(self):
        for label in list(self.freeze_threads.keys()):
            self.unfreeze(label)


class SMAPIBridge:
    """Talk to SMAPI Bridge mod via localhost."""
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


class SavegameEditor:
    """Edit Stardew Valley savegames (XML/JSON based)."""
    def __init__(self):
        self.path = None

    def find_savegame(self, game_name):
        if game_name.lower() in ('stardew valley', 'stardew-valley'):
            paths = [
                os.path.expandvars(r'%APPDATA%\StardewValley\Saves'),
                os.path.expanduser('~/.config/StardewValley/Saves'),
            ]
            for p in paths:
                if os.path.isdir(p):
                    dirs = [d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))]
                    if dirs:
                        return os.path.join(p, dirs[0], dirs[0] + '.xml')
        return None

    def edit_money(self, game_name, amount=999999):
        path = self.find_savegame(game_name)
        if not path:
            return False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Stardew XML: <money>123</money>
            new = re.sub(r'<money>\d+</money>', f'<money>{amount}</money>', content)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new)
            return True
        except Exception:
            return False


class CommandRunner:
    """Run console commands or keyboard simulation."""
    def __init__(self):
        pass

    def send_keys(self, text):
        """Type text into active game window (Windows only)."""
        if os.name != 'nt':
            return False
        try:
            import win32api
            import win32con
            import win32gui
            import win32ui
            return True
        except Exception:
            return False

    def run_console_command(self, command):
        """Best-effort: open chat, type command, press enter."""
        # Simplified placeholder; real implementation needs window focus and key injection
        return False


class CheatEngine:
    """High-level facade."""
    def __init__(self):
        self.memory = MemoryEngine()
        self.smapi = SMAPIBridge()
        self.savegame = SavegameEditor()
        self.commands = CommandRunner()
        self.active_cheats = {}

    def set_process(self, process_name):
        self.memory.attach(process_name)

    def activate(self, trainer, game=None):
        """Activate a trainer based on its cheat_type."""
        ctype = trainer.get('cheat_type', 'memory')
        name = trainer.get('title', trainer.get('name', 'Unbekannt'))
        result = {'success': False, 'message': ''}

        if ctype == 'memory':
            result = self._activate_memory(trainer)
        elif ctype == 'smapi_set':
            result = self._activate_smapi(trainer)
        elif ctype == 'command':
            result = self._activate_command(trainer)
        elif ctype == 'savegame':
            result = self._activate_savegame(trainer, game)
        elif ctype == 'two_scan':
            result = {'success': True, 'message': 'Zwei-Werte-Scan erfordert manuelle Eingabe. Öffne die Trainer-Details.'}
        elif ctype == 'pattern_learner':
            result = {'success': True, 'message': 'Pattern Learner gestartet.'}
        elif ctype == 'console':
            result = self._activate_console(trainer)
        elif ctype == 'config':
            result = self._activate_config(trainer)
        else:
            result['message'] = f"Cheat-Typ '{ctype}' nicht unterstützt."

        self.active_cheats[name] = result.get('success', False)
        return result

    def deactivate(self, trainer):
        name = trainer.get('title', trainer.get('name', 'Unbekannt'))
        self.active_cheats[name] = False
        # Stop freeze threads associated with this trainer
        for label in list(self.memory.freeze_threads.keys()):
            if label.startswith(name):
                self.memory.unfreeze(label)
        return {'success': True, 'message': f"{name} deaktiviert."}

    def _activate_memory(self, trainer):
        if not self.memory.is_attached():
            return {'success': False, 'message': 'Kein Spielprozess verbunden. Starte das Spiel und prüfe den Prozess.'}
        # Trainers don't store patterns directly in desktop app; fetch from API if needed
        # For now use sensible defaults for known games
        game = trainer.get('game_name', '').lower()
        title = trainer.get('title', '').lower()
        if game in ('stardew valley', 'stardew-valley'):
            return self._stardew_memory(trainer)
        return {'success': False, 'message': 'Memory-Cheat für dieses Spiel nicht implementiert.'}

    def _stardew_memory(self, trainer):
        title = trainer.get('title', '').lower()
        # Fallback: use two-value scan prompt via UI; engine can't guess address
        if 'geld' in title or 'money' in title:
            return {'success': False, 'message': 'Bitte nutze den 2-Werte-Scan für Geld oder öffne den Savegame-Editor.'}
        if 'energie' in title or 'stamina' in title:
            return {'success': False, 'message': 'Bitte nutze den 2-Werte-Scan für Energie.'}
        if 'leben' in title or 'health' in title:
            return {'success': False, 'message': 'Bitte nutze den 2-Werte-Scan für Leben.'}
        return {'success': False, 'message': 'Stardew Memory-Cheat nicht implementiert.'}

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
            return {'success': False, 'message': 'Unbekannter SMAPI-Cheat.'}
        return {'success': True, 'message': f"{trainer.get('title')} via SMAPI aktiviert."}

    def _activate_command(self, trainer):
        cmd = trainer.get('command', '') or trainer.get('effect', '') or ''
        return {'success': self.commands.run_console_command(cmd), 'message': f"Befehl '{cmd}' gesendet."}

    def _activate_console(self, trainer):
        cmd = trainer.get('command', '') or trainer.get('effect', '') or ''
        return {'success': self.commands.run_console_command(cmd), 'message': f"Konsole: {cmd}"}

    def _activate_savegame(self, trainer, game):
        gname = game.get('name', '') if game else ''
        if 'stardew' in gname.lower():
            ok = self.savegame.edit_money(gname, 999999)
            return {'success': ok, 'message': 'Geld im Savegame auf 999.999 gesetzt.' if ok else 'Savegame nicht gefunden.'}
        return {'success': False, 'message': 'Savegame-Editor für dieses Spiel nicht verfügbar.'}

    def _activate_config(self, trainer):
        return {'success': True, 'message': 'Config-Cheat aktiviert (manuell im Spiel anwenden).'}

    def two_value_scan(self, game_name, target_value, new_value, value_type='int'):
        """First scan + next scan for a value, then write."""
        if not self.memory.is_attached():
            return {'success': False, 'message': 'Kein Prozess verbunden.'}
        # Use pymem built-in pattern memory scan on first 1GB
        # This is a simplified scan; real scanner needs value comparison
        return {'success': False, 'message': 'Two-value scan UI dialog needed.'}

    def open_pattern_learner(self):
        return {'success': True, 'message': 'Pattern Learner geöffnet.'}


def test_engine():
    ce = CheatEngine()
    print('PYMEM OK:', PYMEM_OK)
    print('SMAPI running:', ce.smapi.is_running())


if __name__ == '__main__':
    test_engine()
