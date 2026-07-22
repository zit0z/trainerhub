"""Background process watcher for running games."""
import time
import logging
import threading
from process_scanner import ProcessScanner

logger = logging.getLogger('sweetcheat')

class ProcessWatcher(threading.Thread):
    def __init__(self, app, interval=10):
        super().__init__(daemon=True)
        self.app = app
        self.scanner = ProcessScanner()
        self.interval = interval
        self._running = False
        self._last = []

    def run(self):
        self._running = True
        while self._running:
            try:
                found = self.scanner.scan()
                new = [f for f in found if f['pid'] not in [x['pid'] for x in self._last]]
                if new:
                    names = ', '.join([f['name'] for f in new])
                    self.app.root.after(0, lambda: self.app.show_toast(f'Spiel erkannt: {names}'))
                    self.app.root.after(0, lambda games=new: self.app.show_running_games(games))
                self._last = found
            except Exception as e:
                logger.error(f"Process watcher error: {e}")
            time.sleep(self.interval)

    def stop(self):
        self._running = False
