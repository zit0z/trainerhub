"""SweetCheat Desktop Application Entry Point"""
import os
import sys
import logging
import traceback
import tkinter as tk
from tkinter import messagebox

# Ensure project root in path
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from logger import get_logger, LOG_FILE
from autostart_module import is_autostart_enabled, set_autostart
from tray_module import SweetCheatTray
from hotkey_module import HotkeyManager
from process_watcher import ProcessWatcher

logger = get_logger('main')
MINIMIZED = '--minimized' in sys.argv


def _global_exception_handler(exc_type, exc_value, exc_tb):
    """Catch-all exception handler for the main thread."""
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Kritischer Fehler",
            f"Ein unerwarteter Fehler ist aufgetreten:\n\n{exc_value}\n\nDetails wurden nach {LOG_FILE} geschrieben."
        )
        root.destroy()
    except Exception:
        pass


def _desktop_notification(title, message, duration=3000):
    """Native desktop-style notification popup."""
    try:
        root = tk.Tk()
        root.withdraw()
        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.configure(bg='#0f1016')
        win.geometry(f'320x80+{root.winfo_screenwidth() - 340}+20')
        tk.Label(win, text=title, font=('Rajdhani', 12, 'bold'), fg='#00f0ff', bg='#0f1016').pack(pady=(10, 4))
        tk.Label(win, text=message, font=('Segoe UI', 10), fg='#f8fafc', bg='#0f1016').pack()
        root.after(duration, win.destroy)
        root.after(duration + 100, root.destroy)
        root.mainloop()
    except Exception as e:
        logger.error(f"Notification error: {e}")


def _attach_background_services(app):
    """Start system tray, global hotkeys and process watcher."""
    try:
        tray = SweetCheatTray(app)
        tray.start()
        app.tray = tray
        logger.info("System tray started")
    except Exception as e:
        logger.warning(f"System tray not available: {e}")

    try:
        hk = HotkeyManager()
        hk.register('ctrl+shift+s', lambda: app.root.after(0, app.show_window))
        hk.register('ctrl+shift+g', lambda: app.root.after(0, app.show_games_library))
        hk.start()
        app.hotkeys = hk
        logger.info("Global hotkeys registered")
    except Exception as e:
        logger.warning(f"Global hotkeys not available: {e}")

    try:
        watcher = ProcessWatcher(app, interval=15)
        watcher.start()
        app.watcher = watcher
        logger.info("Process watcher started")
    except Exception as e:
        logger.warning(f"Process watcher not available: {e}")


def main():
    sys.excepthook = _global_exception_handler
    logger.info(f"SweetCheat starting. Python {sys.version}. CWD: {os.getcwd()}. Minimized: {MINIMIZED}")

    try:
        from gui_module import main as gui_main
        app = gui_main(minimized=MINIMIZED)
        if app:
            _attach_background_services(app)
            app.root.mainloop()
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
