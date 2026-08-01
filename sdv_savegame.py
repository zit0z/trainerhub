"""Stardew Valley Savegame Editor."""
import os
import json
import shutil
import glob
import time
from pathlib import Path

SAVE_PATTERN = os.path.expandvars(r'%APPDATA%\StardewValley\Saves\*')
FARMER_MONEY_FIELDS = ['money', 'totalMoneyEarned']

def find_save_folders():
    """Return list of Stardew Valley save folders."""
    folders = glob.glob(SAVE_PATTERN)
    return [f for f in folders if os.path.isdir(f)]

def find_save_file(folder):
    """Find the main SaveGameInfo.json or *.xml save in folder."""
    candidates = [
        os.path.join(folder, 'SaveGameInfo.json'),
    ]
    # Stardew uses XML per farmname
    xml_files = glob.glob(os.path.join(folder, '*.xml'))
    candidates.extend(xml_files)
    return [c for c in candidates if os.path.exists(c)]

def backup_save(folder):
    backup_dir = Path.home() / 'Desktop' / 'SweetCheat_Backups' / 'StardewValley'
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime('%Y%m%d_%H%M%S')
    dest = backup_dir / f"sv_backup_{ts}"
    shutil.copytree(folder, dest)
    return str(dest)

def edit_money_xml(filepath, amount=999999):
    """Edit money in Stardew XML save."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        import re
        # Replace <money>XXX</money>
        new_content = re.sub(r'(<money>)\d+(\u003c/money>)', r'\g<1>%d\g<2>' % amount, content)
        if new_content == content:
            return False, 'Kein <money> Feld in Savegame gefunden'
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True, f'Geld auf {amount} gesetzt'
    except Exception as e:
        return False, str(e)

def edit_savegame_json(filepath, amount=999999):
    """Edit money in SaveGameInfo.json if present."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'money' in data:
            data['money'] = amount
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True, f'SaveGameInfo Geld auf {amount} gesetzt'
    except Exception as e:
        return False, str(e)

def apply_cheat(cheat_type='money', value=999999):
    folders = find_save_folders()
    if not folders:
        return False, 'Keine Stardew Valley Saves gefunden. Starte das Spiel und speichere zuerst.'
    results = []
    for folder in folders:
        backup = backup_save(folder)
        files = find_save_file(folder)
        for fp in files:
            if fp.endswith('.json'):
                ok, msg = edit_savegame_json(fp, value)
            else:
                ok, msg = edit_money_xml(fp, value)
            results.append(f"{os.path.basename(folder)}: {msg} (Backup: {backup})")
    return True, '\n'.join(results)
