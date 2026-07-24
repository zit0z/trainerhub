"""In-app changelog for SweetCheat."""
import os
import sys
import json
import logging
import requests
import tkinter as tk
from tkinter import scrolledtext

logger = logging.getLogger('sweetcheat')
CHANGELOG_URL = 'https://sayfespace.online/trainerhub/api/changelog.php'

class ChangelogWindow:
    def __init__(self, parent, version):
        self.parent = parent
        self.version = version

    def show(self):
        try:
            win = tk.Toplevel(self.parent)
            win.title(f'Changelog — {self.version}')
            win.configure(bg='#0f1016')
            win.geometry('600x450')
            tk.Label(win, text=f'Was ist neu in v{self.version}?', font=('Rajdhani', 18, 'bold'), fg='#00f0ff', bg='#0f1016').pack(pady=(16, 12))
            txt = scrolledtext.ScrolledText(win, wrap='word', bg='#141821', fg='#f8fafc', font=('Segoe UI', 11), borderwidth=0, padx=12, pady=12)
            txt.pack(fill='both', expand=True, padx=16, pady=(0, 16))
            txt.insert('end', 'Lade Changelog...')
            txt.config(state='disabled')
            def load():
                try:
                    r = requests.get(CHANGELOG_URL, timeout=8)
                    data = r.json()
                    text = data.get('body', 'Keine Details verfügbar.')
                    txt.config(state='normal')
                    txt.delete('1.0', 'end')
                    txt.insert('end', text)
                    txt.config(state='disabled')
                except Exception as e:
                    txt.config(state='normal')
                    txt.delete('1.0', 'end')
                    txt.insert('end', f'Changelog konnte nicht geladen werden.\n{e}')
                    txt.config(state='disabled')
            import threading
            threading.Thread(target=load, daemon=True).start()
        except Exception as e:
            logger.error(f"Changelog window error: {e}")
