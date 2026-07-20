"""TrainerHub Desktop Application - Optimized Startup"""
import sys
import os
import json
import tkinter as tk
from tkinter import messagebox

# Ensure AppData/config directory exists
CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'TrainerHub')
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {'email': '', 'token': '', 'api_base': 'https://sayfespace.online/trainerhub/api'}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f)
    except Exception as e:
        print(f"Config save error: {e}")

def main():
    try:
        config = load_config()
        root = tk.Tk()
        root.withdraw()
        from gui_module import TrainerHubGUI
        app = TrainerHubGUI(root)
        root.deiconify()
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Fehler", f"App-Start fehlgeschlagen: {e}")
        raise

if __name__ == '__main__':
    main()
