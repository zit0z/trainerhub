"""Process scanner for finding game executables."""
import sys
import logging
import subprocess
import json
import re

logger = logging.getLogger('SweetCheat.ProcessScanner')
WINDOWS = sys.platform == 'win32'

if WINDOWS:
    try:
        import psutil
    except ImportError:
        psutil = None
else:
    psutil = None


class ProcessScanner:
    def __init__(self):
        self.known_games = {
            'Stardew Valley.exe': {'slug': 'stardew-valley', 'name': 'Stardew Valley'},
            'StardewModdingAPI.exe': {'slug': 'stardew-valley', 'name': 'Stardew Valley (SMAPI)'},
        }

    def scan(self):
        """Return list of detected running games."""
        results = []
        if not WINDOWS or not psutil:
            logger.warning("psutil not available on Windows, process scanning disabled")
            return results
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                name = proc.info.get('name') or ''
                exe = proc.info.get('exe') or ''
                base = name or (exe.split('\\')[-1] if exe else '')
                if base in self.known_games:
                    info = self.known_games[base].copy()
                    info['pid'] = proc.info.get('pid')
                    info['exe'] = exe
                    results.append(info)
        except Exception as e:
            logger.exception(f"Process scan failed: {e}")
        return results

    def find_process(self, process_name):
        if not WINDOWS or not psutil:
            return None
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                if proc.info.get('name', '').lower() == process_name.lower():
                    return proc.info
        except Exception as e:
            logger.error(f"find_process error: {e}")
        return None
