import os
import sys
import time

# Windows-only named pipe support
try:
    import win32file
    import win32pipe
    import pywintypes
    PIPE_AVAILABLE = True
except ImportError:
    PIPE_AVAILABLE = False

PIPE_NAME = r'\\\\.\\pipe\\TrainerHubStardew'

class StardewBridgeClient:
    def __init__(self):
        self.handle = None

    def is_available(self):
        return PIPE_AVAILABLE and sys.platform == 'win32'

    def connect(self, timeout=2.0):
        if not self.is_available():
            return False
        start = time.time()
        while time.time() - start < timeout:
            try:
                self.handle = win32file.CreateFile(
                    PIPE_NAME,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                win32pipe.SetNamedPipeHandleState(self.handle, win32pipe.PIPE_READMODE_MESSAGE, None, None)
                return True
            except pywintypes.error:
                time.sleep(0.2)
        return False

    def send(self, command):
        if not self.handle:
            return None
        try:
            win32file.WriteFile(self.handle, (command + '\n').encode('utf-8'))
            data = b''
            while True:
                try:
                    hr, chunk = win32file.ReadFile(self.handle, 4096)
                    data += chunk
                    if len(chunk) < 4096:
                        break
                except pywintypes.error as e:
                    if e.winerror == win32file.ERROR_MORE_DATA:
                        continue
                    break
            return data.decode('utf-8').strip()
        except Exception as e:
            return f'error:{e}'

    def get(self, stat):
        return self.send(f'get:{stat}')

    def set(self, stat, value):
        return self.send(f'set:{stat}:{value}')

    def close(self):
        if self.handle:
            try:
                win32file.CloseHandle(self.handle)
            except Exception:
                pass
            self.handle = None
