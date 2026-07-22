"""SweetCheat Desktop Application - Entry Point"""
import sys
import os
import json
import logging
import traceback
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

# Ensure config directory exists early
CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SweetCheat')
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
LOG_FILE = os.path.join(CONFIG_DIR, 'sweetcheat.log')

# Setup logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('SweetCheat')


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                # Validate expected keys
                if not isinstance(cfg, dict):
                    raise ValueError('Config is not a dict')
                cfg.setdefault('api_key', None)
                cfg.setdefault('api_base', 'https://sayfespace.online/sweetcheat/api')
                return cfg
    except Exception as e:
        logger.warning(f"Config load failed ({e}), using defaults")
    return {'api_key': None, 'api_base': 'https://sayfespace.online/sweetcheat/api'}


def save_config(cfg):
    try:
        tmp = CONFIG_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, CONFIG_FILE)
        logger.info("Config saved")
    except Exception as e:
        logger.error(f"Config save error: {e}")


def _global_exception_handler(exc_type, exc_value, exc_tb):
    msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical(f"Uncaught exception: {msg}")
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Kritischer Fehler", f"Ein unerwarteter Fehler ist aufgetreten:\n\n{exc_value}\n\nDetails wurden nach {LOG_FILE} geschrieben.")
        root.destroy()
    except Exception:
        pass


def show_notification(title, message, duration=3000):
    try:
        from tkinter import Toplevel, Label
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        win = Toplevel(root)
        win.overrideredirect(True)
        win.configure(bg='#0f1016')
        win.geometry('320x80+%d+%d' % (root.winfo_screenwidth() - 340, 20))
        Label(win, text=title, font=('Rajdhani', 12, 'bold'), fg='#00f0ff', bg='#0f1016').pack(pady=(10, 4))
        Label(win, text=message, font=('Segoe UI', 10), fg='#f8fafc', bg='#0f1016').pack()
        root.after(duration, win.destroy)
        root.after(duration + 100, root.destroy)
        root.mainloop()
    except Exception as e:
        logger.error(f"Notification error: {e}")


def main():
    sys.excepthook = _global_exception_handler
    logger.info(f"SweetCheat starting. Python {sys.version}. CWD: {os.getcwd()}")
    try:
        from gui_module import main as gui_main
        gui_main()
    except Exception as e:
        logger.exception("App start failed")
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fehler", f"App-Start fehlgeschlagen: {e}")
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == '__main__':
    main()
