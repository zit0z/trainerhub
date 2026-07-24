"""
Self-implemented savegame trainers for games with publicly documented save formats.
No copyrighted code - uses publicly documented XML/JSON/INI formats.
"""
import os
import glob
import json
import shutil
import struct
import configparser
import xml.etree.ElementTree as ET
from datetime import datetime

class SavegameTrainerBase:
    def find_saves(self):
        return []
    
    def read(self, path):
        return {}
    
    def write(self, path, changes):
        return False
    
    def backup(self, path):
        backup_path = path + f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(path, backup_path)
        return backup_path

class StardewValleySavegame(SavegameTrainerBase):
    def find_saves(self):
        base = os.path.expandvars(r'%APPDATA%\\StardewValley\\Saves')
        if not os.path.exists(base):
            return []
        return glob.glob(os.path.join(base, '*', '*'))
    
    def read(self, path):
        tree = ET.parse(path)
        root = tree.getroot()
        player = root.find('player')
        return {
            'money': int(player.find('money').text) if player.find('money') is not None else 0,
            'health': int(player.find('health').text) if player.find('health') is not None else 0,
            'maxHealth': int(player.find('maxHealth').text) if player.find('maxHealth') is not None else 0,
            'stamina': int(player.find('stamina').text) if player.find('stamina') is not None else 0,
            'maxStamina': int(player.find('maxStamina').text) if player.find('maxStamina') is not None else 0,
        }
    
    def write(self, path, changes):
        self.backup(path)
        tree = ET.parse(path)
        root = tree.getroot()
        player = root.find('player')
        for key, value in changes.items():
            elem = player.find(key)
            if elem is not None:
                elem.text = str(value)
        tree.write(path, encoding='utf-8', xml_declaration=True)
        return True

class MinecraftSavegame(SavegameTrainerBase):
    """Minecraft level.dat uses NBT format; we provide documented command-based trainer instead."""
    def find_saves(self):
        return []
    
    def read(self, path):
        return {'note': 'Minecraft verwendet NBT-Binary. Nutze offizielle Konsolenbefehle im Spiel.'}

class FactorioSavegame(SavegameTrainerBase):
    """Factorio uses compressed binary; official console commands are better."""
    pass

class Witcher3Savegame(SavegameTrainerBase):
    """Witcher 3 saves are compressed binary; official console commands are better."""
    pass

class CitiesSkylinesSavegame(SavegameTrainerBase):
    """Cities: Skylines has built-in cheat panel via Alt+F12."""
    def read(self, path):
        return {'note': 'Nutze Alt+F12 im Spiel für den Entwickler-Modus.'}

SUPPORTED_SAVEGAME_TRAINERS = {
    'stardew-valley': StardewValleySavegame,
    'minecraft-java': MinecraftSavegame,
    'factorio': FactorioSavegame,
    'witcher-3': Witcher3Savegame,
    'cities-skylines': CitiesSkylinesSavegame,
}

# Generic JSON savegame editor
class JsonSavegameEditor:
    def __init__(self, save_path, field_map):
        self.save_path = save_path
        self.field_map = field_map
    
    def read(self):
        with open(self.save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result = {}
        for key, path in self.field_map.items():
            val = data
            for p in path.split('.'):
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    val = None
                    break
            result[key] = val
        return result
    
    def write(self, changes):
        shutil.copy2(self.save_path, self.save_path + f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        with open(self.save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key, value in changes.items():
            if key in self.field_map:
                path = self.field_map[key]
                parts = path.split('.')
                target = data
                for p in parts[:-1]:
                    target = target.setdefault(p, {})
                target[parts[-1]] = value
        with open(self.save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
