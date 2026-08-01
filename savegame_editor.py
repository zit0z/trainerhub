"""Generic savegame editor bridge for SweetCheat desktop app."""
import os
import json
import shutil
import glob
import time
import re
from pathlib import Path

def discover_save(game_name):
    """Try common save locations for a game name."""
    candidates = [
        os.path.expandvars(r'%APPDATA%') + f'\\{game_name}',
        os.path.expandvars(r'%USERPROFILE%\\Documents\\My Games\\{game_name}\\Saves'),
        os.path.expandvars(r'%USERPROFILE%\\Documents\\My Games\\{game_name}'),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None

def backup_and_edit(save_dir, field='money', value='999999'):
    if not save_dir or not os.path.isdir(save_dir):
        return False, f'Savegame-Verzeichnis nicht gefunden: {save_dir}'
    backup_dir = Path.home() / 'Desktop' / 'SweetCheat_Backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime('%Y%m%d_%H%M%S')
    dest = backup_dir / f"save_backup_{ts}"
    shutil.copytree(save_dir, dest)

    json_files = glob.glob(os.path.join(save_dir, '**', '*.json'), recursive=True)
    if not json_files:
        return False, 'Keine JSON-Savegame-Dateien gefunden'

    modified = []
    for fp in json_files:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if _set_nested(data, field.split('.'), value):
                with open(fp, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                modified.append(os.path.basename(fp))
        except Exception as e:
            pass

    if modified:
        return True, f"Backup: {dest} | Bearbeitet: {', '.join(modified)}"
    return False, 'Keine passenden Felder zum Bearbeiten gefunden'

def _set_nested(data, keys, value):
    if not keys:
        return False
    if len(keys) == 1:
        if keys[0] in data:
            data[keys[0]] = int(value) if str(value).isdigit() else value
            return True
        return False
    if keys[0] in data and isinstance(data[keys[0]], dict):
        return _set_nested(data[keys[0]], keys[1:], value)
    return False

def edit_xml_money(filepath, amount):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        new = re.sub(r'(<money>)\d+(\u003c/money>)', r'\g<1>%d\g<2>' % amount, content)
        if new == content:
            return False, 'money tag not found'
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new)
        return True, 'money updated'
    except Exception as e:
        return False, str(e)
