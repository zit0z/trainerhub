"""System tray integration for SweetCheat desktop app."""
import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import Menu

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except Exception as e:
    TRAY_AVAILABLE = False
    logging.warning(f"pystray/PIL not available: {e}")

logger = logging.getLogger('sweetcheat')

def create_tray_image():
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color='black')
    dc = ImageDraw.Draw(image)
    dc.rectangle([8, 8, width-8, height-8], outline='#00f0ff', width=3)
    dc.polygon([(width//2, 18), (18, height-18), (width-18, height-18)], fill='#00f0ff')
    return image

class SweetCheatTray:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self._thread = None

    def start(self):
        if not TRAY_AVAILABLE:
            logger.info("System tray not available")
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            menu = Menu(
                MenuItem('Öffnen', self._show_window),
                MenuItem('Spiele scannen', self._scan_games),
                Menu.SEPARATOR,
                MenuItem('Beenden', self._quit)
            )
            self.icon = pystray.Icon('SweetCheat', create_tray_image(), 'SweetCheat', menu)
            self.icon.run()
        except Exception as e:
            logger.error(f"Tray error: {e}")

    def _show_window(self, icon=None, item=None):
        self.app.root.after(0, self.app.show_window)

    def _scan_games(self, icon=None, item=None):
        self.app.root.after(0, self.app._scan_processes)

    def _quit(self, icon=None, item=None):
        self.app.root.after(0, self.app.on_close)

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e:
                logger.error(f"Tray stop error: {e}")

class MenuItem:
    def __init__(self, text, action):
        self.text = text
        self.action = action
