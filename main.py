"""TrainerHub Desktop Application - Entry Point"""
import sys
import os
import json
import tkinter as tk
from tkinter import messagebox

CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'TrainerHub')
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')


def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'api_key': None, 'api_base': 'https://sayfespace.online/trainerhub/api'}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
    except Exception as e:
        print(f"Config save error: {e}")


def main():
    try:
        from gui_module import main as gui_main
        gui_main()
    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Fehler", f"App-Start fehlgeschlagen: {e}")
        raise


if __name__ == '__main__':
    main()
