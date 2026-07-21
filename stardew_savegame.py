"""Stardew Valley savegame editor helpers for TrainerHub.

Works on standard Windows save location:
%APPDATA%/StardewValley/Saves/<farmerName>_<id>/<farmerName>_<id>

Uses ElementTree for safe XML editing. Always creates backups.
"""
import os
import glob
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

SAVE_DIR = Path(os.environ.get('APPDATA', '')) / 'StardewValley' / 'Saves'


def _find_save_folders():
    """Return list of save folder paths."""
    if not SAVE_DIR.exists():
        return []
    return [p for p in SAVE_DIR.iterdir() if p.is_dir()]


def _find_save_file(folder):
    """Find SaveGameInfo / host XML inside a save folder."""
    candidates = list(folder.glob('*.xml'))
    # Prefer largest XML (host save)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0]


def _backup(path):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = Path(str(path) + f'.backup_{ts}')
    shutil.copy2(path, backup)
    return str(backup)


def edit_save(cheat, value=None):
    """Apply a savegame cheat. Returns dict with success/message."""
    folders = _find_save_folders()
    if not folders:
        return {'success': False, 'message': 'Kein Stardew Valley Savegame gefunden.'}
    # Use most recently modified save
    folder = max(folders, key=lambda p: max((c.stat().st_mtime for c in p.iterdir() if c.is_file()), default=0))
    save_file = _find_save_file(folder)
    if not save_file:
        return {'success': False, 'message': 'Keine Savegame-XML im Save-Ordner gefunden.'}

    name = cheat.get('name', '').lower()
    try:
        tree = ET.parse(save_file)
        root = tree.getroot()
        player = root.find('player')
        if player is None:
            return {'success': False, 'message': 'Spielerdaten nicht im Savegame gefunden.'}

        changes = []

        if 'geld' in name or 'money' in name:
            money = player.find('money')
            if money is None:
                money = ET.SubElement(player, 'money')
            money.text = str(value if value is not None else 999999)
            changes.append(f'Geld = {money.text}')

        elif 'leben' in name or 'health' in name:
            health = player.find('health')
            if health is None:
                health = ET.SubElement(player, 'health')
            max_health = player.find('maxHealth')
            max_h = int(max_health.text) if max_health is not None and max_health.text else 100
            health.text = str(max_h)
            changes.append(f'Leben = {max_h}')

        elif 'energie' in name or 'stamina' in name:
            stamina = player.find('stamina')
            if stamina is None:
                stamina = ET.SubElement(player, 'stamina')
            max_stamina = player.find('maxStamina')
            max_s = int(max_stamina.text) if max_stamina is not None and max_stamina.text else 270
            stamina.text = str(max_s)
            changes.append(f'Energie = {max_s}')

        elif 'rucksack' in name or 'backpack' in name:
            max_items = player.find('maxItems')
            if max_items is None:
                max_items = ET.SubElement(player, 'maxItems')
            max_items.text = str(value if value is not None else 36)
            changes.append(f'Rucksack = {max_items.text}')

        elif 'max stats' in name or 'alle stats' in name:
            for skill_name in ['farmingLevel', 'miningLevel', 'foragingLevel', 'fishingLevel', 'combatLevel']:
                el = player.find(skill_name)
                if el is None:
                    el = ET.SubElement(player, skill_name)
                el.text = str(value if value is not None else 10)
            changes.append('Alle Skills = 10')

        elif 'level' in name or 'erfahrung' in name:
            for skill_name in ['farmingLevel', 'miningLevel', 'foragingLevel', 'fishingLevel', 'combatLevel']:
                el = player.find(skill_name)
                if el is None:
                    el = ET.SubElement(player, skill_name)
                el.text = str(value if value is not None else 10)
            changes.append('Alle Skills = 10')

        if not changes:
            return {'success': False, 'message': f'Unbekannter Savegame-Cheat: {name}'}

        backup_path = _backup(save_file)
        tree.write(save_file, encoding='UTF-8', xml_declaration=True)
        return {
            'success': True,
            'message': f"Savegame bearbeitet: {', '.join(changes)}. Starte Stardew Valley neu. Backup: {Path(backup_path).name}"
        }
    except Exception as e:
        return {'success': False, 'message': f'Savegame-Editor Fehler: {str(e)[:200]}'}


def list_saves():
    """Return save file paths for UI display."""
    folders = _find_save_folders()
    out = []
    for f in folders:
        sf = _find_save_file(f)
        if sf:
            out.append({'folder': str(f), 'file': str(sf), 'modified': sf.stat().st_mtime})
    out.sort(key=lambda x: x['modified'], reverse=True)
    return out
