"""Desktop trainer activation engine."""
import os
import sys
import json
import time
import logging
import threading
import shutil
import subprocess
import glob
import re
from pathlib import Path

logger = logging.getLogger('SweetCheat.Activation')
WINDOWS = sys.platform == 'win32'

class ActivationEngine:
    def __init__(self, api_client=None):
        self.api = api_client
        self.active_trainers = {}
        self._lock = threading.Lock()

    def can_activate(self, trainer):
        if trainer.get('locked') or trainer.get('is_premium'):
            return False, 'Premium-Trainer erfordert Abonnement'
        method = trainer.get('method', 'memory')
        if method == 'memory' and not WINDOWS:
            return False, 'Memory-Methoden benötigen Windows'
        return True, 'OK'

    def _find_process(self, process_name):
        if not WINDOWS or not process_name:
            return None
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    return proc.info['pid']
        except Exception as e:
            logger.error(f"Process lookup failed: {e}")
        return None

    def _run_console_command(self, game_info, command, params):
        game = game_info or {}
        process_name = game.get('process_name') or game.get('process') or ''
        if not process_name:
            return False, 'Kein Prozessname für Konsole-Befehl angegeben'
        pid = self._find_process(process_name)
        if not pid:
            return False, f"Spielprozess '{process_name}' nicht gefunden. Starte das Spiel zuerst."
        return True, f"Befehl '{command}' vorbereitet (PID {pid}) — vollständige Injection erfordert SMAPI/Bridge-Setup"

    def _edit_savegame(self, trainer, game_info):
        try:
            params = json.loads(trainer.get('params') or '{}')
        except Exception:
            params = {}
        game = game_info or {}
        game_name = game.get('name') or trainer.get('game_name') or 'Game'
        field = params.get('field', 'money')
        value = params.get('value', '999999')
        save_dir = params.get('path')
        if not save_dir:
            save_dir = self._discover_save(game_name)
        if not save_dir:
            return False, f"Kein Savegame-Verzeichnis für '{game_name}' gefunden"
        try:
            from savegame_editor import backup_and_edit
            ok, msg = backup_and_edit(save_dir, field, value)
            return ok, msg
        except Exception as e:
            return False, f"Savegame-Edit fehlgeschlagen: {e}"

    def _discover_save(self, game_name):
        candidates = [
            os.path.expandvars(r'%APPDATA%') + f'\\{game_name}',
            os.path.expandvars(r'%USERPROFILE%\\Documents\\My Games\\{game_name}\\Saves'),
            os.path.expandvars(r'%USERPROFILE%\\Documents\\My Games\\{game_name}'),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        return None

    def _stardew_cheat(self, trainer):
        try:
            from sdv_savegame import apply_cheat
            return apply_cheat('money', 999999)
        except Exception as e:
            return False, f"Stardew Cheat fehlgeschlagen: {e}"

    def _memory_cheat(self, trainer, game_info):
        return False, "Memory-Cheat erfordert Cheat-Engine-Integration. Diese Funktion ist in der aktuellen Version als Platzhalter markiert."

    def _backup_savegame(self, trainer, game_info):
        try:
            params = json.loads(trainer.get('params') or '{}')
        except Exception:
            params = {}
        game = game_info or {}
        game_name = game.get('name') or 'Game'
        save_dir = params.get('path') or self._discover_save(game_name)
        if not save_dir or not os.path.isdir(save_dir):
            return False, f"Savegame-Verzeichnis nicht gefunden: {save_dir}"
        backup_dir = Path.home() / 'Desktop' / 'SweetCheat_Backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime('%Y%m%d_%H%M%S')
        dest = backup_dir / f"{game_name}_backup_{ts}"
        try:
            shutil.copytree(save_dir, dest)
            return True, f"Backup erstellt: {dest}"
        except Exception as e:
            return False, f"Backup fehlgeschlagen: {e}"

    def activate(self, trainer, game_info=None, callback=None):
        def _run():
            try:
                tid = trainer.get('trainer_id')
                name = trainer.get('name', 'Unbekannt')
                method = trainer.get('method', 'memory')
                action = trainer.get('action', '')
                logger.info(f"Activating trainer {tid}: {name} (method={method}, action={action})")

                if self.api:
                    try:
                        self.api.activate_log(tid, success=1, action='desktop_activate')
                    except Exception as e:
                        logger.error(f"Activation log failed: {e}")

                # Stardew specific detection
                game_name = (game_info or {}).get('name', '')
                if 'stardew' in name.lower() or 'stardew' in game_name.lower():
                    ok, msg = self._stardew_cheat(trainer)
                elif method == 'console':
                    ok, msg = self._run_console_command(game_info, action, trainer.get('params', ''))
                elif method == 'savegame':
                    if action == 'copy':
                        ok, msg = self._backup_savegame(trainer, game_info)
                    else:
                        ok, msg = self._edit_savegame(trainer, game_info)
                elif method == 'memory':
                    ok, msg = self._memory_cheat(trainer, game_info)
                else:
                    ok, msg = True, f"'{name}' aktiviert (Demo-Modus)"

                if ok:
                    with self._lock:
                        self.active_trainers[tid] = {'name': name, 'activated_at': time.time(), 'game': game_info}

                if callback:
                    callback(ok, msg)
            except Exception as e:
                logger.exception(f"Activation error: {e}")
                if callback:
                    callback(False, str(e))

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    def deactivate(self, trainer_id):
        with self._lock:
            if trainer_id in self.active_trainers:
                del self.active_trainers[trainer_id]
                return True
        return False

    def is_active(self, trainer_id):
        with self._lock:
            return trainer_id in self.active_trainers

    def list_active(self):
        with self._lock:
            return list(self.active_trainers.values())
