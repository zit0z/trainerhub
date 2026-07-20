"""
Stardew Valley Savegame Trainer
Reads/writes player stats in %AppData%\StardewValley\Saves\
Works for Steam/GOG singleplayer saves.
"""
import os
import json
import glob
import xml.etree.ElementTree as ET

SAVE_DIR = os.path.join(os.environ.get('APPDATA', ''), 'StardewValley', 'Saves')

def list_saves():
    if not os.path.exists(SAVE_DIR):
        return []
    saves = []
    for folder in os.listdir(SAVE_DIR):
        path = os.path.join(SAVE_DIR, folder)
        if os.path.isdir(path):
            files = glob.glob(os.path.join(path, '*.xml'))
            if files:
                saves.append({'name': folder, 'path': files[0]})
    return saves

def read_save(path):
    tree = ET.parse(path)
    root = tree.getroot()
    player = root.find('player')
    if player is None:
        return None
    money = player.find('money')
    total_money_earned = player.find('totalMoneyEarned')
    health = player.find('health')
    max_health = player.find('maxHealth')
    stamina = player.find('stamina')
    max_stamina = player.find('maxStamina')
    return {
        'money': int(money.text) if money is not None else 0,
        'total_money_earned': int(total_money_earned.text) if total_money_earned is not None else 0,
        'health': int(health.text) if health is not None else 0,
        'max_health': int(max_health.text) if max_health is not None else 0,
        'stamina': int(stamina.text) if stamina is not None else 0,
        'max_stamina': int(max_stamina.text) if max_stamina is not None else 0,
    }

def write_save(path, values):
    tree = ET.parse(path)
    root = tree.getroot()
    player = root.find('player')
    if player is None:
        return False
    
    mapping = {
        'money': 'money',
        'total_money_earned': 'totalMoneyEarned',
        'health': 'health',
        'max_health': 'maxHealth',
        'stamina': 'stamina',
        'max_stamina': 'maxStamina',
    }
    for key, xml_tag in mapping.items():
        if key in values:
            el = player.find(xml_tag)
            if el is not None:
                el.text = str(int(values[key]))
    
    # Backup
    backup_path = path + '.backup'
    if not os.path.exists(backup_path):
        import shutil
        shutil.copy2(path, backup_path)
    
    tree.write(path, encoding='utf-8', xml_declaration=True)
    return True

if __name__ == '__main__':
    saves = list_saves()
    print(json.dumps(saves, indent=2))
