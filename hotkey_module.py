"""Global hotkey support for SweetCheat desktop app."""
import logging
import threading

logger = logging.getLogger('sweetcheat')

class HotkeyManager:
    def __init__(self):
        self.hotkeys = {}
        self._listener = None
        self._running = False

    def register(self, keys, callback):
        self.hotkeys[keys] = callback

    def start(self):
        try:
            import keyboard
            for keys, cb in self.hotkeys.items():
                keyboard.add_hotkey(keys, cb)
            self._running = True
            logger.info("Global hotkeys registered")
        except Exception as e:
            logger.warning(f"Global hotkeys not available: {e}")

    def stop(self):
        try:
            import keyboard
            for keys in self.hotkeys:
                keyboard.remove_hotkey(keys)
        except Exception as e:
            logger.warning(f"Hotkey stop error: {e}")

    def register_default(self, app):
        self.register('ctrl+shift+s', lambda: app.root.after(0, app.show_window))
        self.register('ctrl+shift+g', lambda: app.root.after(0, app.show_games_library))
