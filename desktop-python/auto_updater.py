"""Auto-updater for SweetCheat desktop app."""
import os
import sys
import json
import logging
import webbrowser
import requests
import threading
import tkinter as tk
from tkinter import messagebox

logger = logging.getLogger('sweetcheat')

UPDATE_URL = 'https://sayfespace.online/trainerhub/api/version.php'

class AutoUpdater:
    def __init__(self, app):
        self.app = app
        self.current_version = getattr(app, 'version', '0.0.0')

    def check(self, silent=False):
        def run():
            try:
                r = requests.get(UPDATE_URL, timeout=8)
                data = r.json()
                latest = data.get('version')
                if latest and latest != self.current_version:
                    logger.info(f"Update available: {latest}")
                    self.app.root.after(0, lambda: self._prompt_update(data.get('installer_url', UPDATE_URL.replace('api/version.php', 'setup')), latest))
                elif not silent:
                    self.app.root.after(0, lambda: self.app.show_toast('SweetCheat ist aktuell'))
            except Exception as e:
                logger.warning(f"Update check failed: {e}")
                if not silent:
                    self.app.root.after(0, lambda: self.app.show_toast('Update-Check fehlgeschlagen'))
        threading.Thread(target=run, daemon=True).start()

    def _prompt_update(self, url, version):
        try:
            win = tk.Toplevel(self.app.root)
            win.title('Update verfügbar')
            win.configure(bg='#0f1016')
            win.geometry('420x200')
            tk.Label(win, text=f'Version {version} ist verfügbar!', font=('Rajdhani', 16, 'bold'), fg='#00f0ff', bg='#0f1016').pack(pady=(20, 10))
            tk.Label(win, text='Möchtest du das Update herunterladen?', font=('Segoe UI', 11), fg='#f8fafc', bg='#0f1016').pack(pady=(0, 20))
            def download():
                webbrowser.open(url)
                win.destroy()
            tk.Button(win, text='Herunterladen', command=download, bg='#00f0ff', fg='#0a0a0f', font=('Segoe UI', 10, 'bold'), borderwidth=0).pack(side='left', padx=20, pady=10)
            tk.Button(win, text='Später', command=win.destroy, bg='#1e293b', fg='#f8fafc', font=('Segoe UI', 10), borderwidth=0).pack(side='right', padx=20, pady=10)
        except Exception as e:
            logger.error(f"Update prompt error: {e}")
