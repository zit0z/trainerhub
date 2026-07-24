"""Windows autostart helper."""
import os
import sys
import logging

try:
    import winreg
    WINREG_AVAILABLE = True
except Exception:
    WINREG_AVAILABLE = False

logger = logging.getLogger('sweetcheat')
APP_NAME = 'SweetCheat'

def is_autostart_enabled():
    if not WINREG_AVAILABLE:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\\Microsoft\\Windows\\CurrentVersion\\Run', 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        logger.error(f"Autostart check error: {e}")
        return False

def set_autostart(enabled, exe_path=None):
    if not WINREG_AVAILABLE:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\\Microsoft\\Windows\\CurrentVersion\\Run', 0, winreg.KEY_SET_VALUE)
        if enabled:
            path = exe_path or sys.executable
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{path}" --minimized')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logger.error(f"Autostart set error: {e}")
        return False
