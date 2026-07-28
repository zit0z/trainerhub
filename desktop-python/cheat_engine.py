"""SweetCheat Engine — Advanced Memory & Savegame Runtime."""
import os
import re
import sys
import json
import subprocess
import shutil
from datetime import datetime

try:
    import pymem
    import pymem.process
except ImportError:
    # We simulate the interface if pymem is missing for the build, 
    # but in the real Windows EXE it will be installed.
    class MockPymem:
        def __init__(self, *args, **kwargs): self.process = None
        def read_int(self, addr): return 0
        def write_int(self, addr, val): return True
        def pattern_scan_all(self, pattern): return 0x0
    pymem = type('obj', (object,), {'Pymem': MockPymem})

class CheatEngine:
    def __init__(self):
        self.active_process = None
        self.pm = None

    def attach(self, process_name):
        """Attaches to a process using pymem."""
        try:
            self.pm = pymem.Pymem(process_name)
            self.active_process = process_name
            return True, f"Attached to {process_name}"
        except Exception as e:
            return False, f"Could not attach: {str(e)}"

    def write_memory_value(self, address, value, size=4):
        """Writes a value to a specific memory address."""
        if not self.pm: return False, "Not attached"
        try:
            if size == 4: self.pm.write_int(address, int(value))
            elif size == 8: self.pm.write_longlong(address, int(value))
            return True, "Value written"
        except Exception as e:
            return False, str(e)

    def find_and_patch(self, pattern, offset, value, size=4):
        """
        The 'Plitch/WeMod' Method: 
        1. Search for a unique byte pattern (AOB).
        2. Add the offset to find the exact value address.
        3. Patch it.
        """
        if not self.pm: return False, "Not attached"
        try:
            # pattern example: "00 00 00 00 00 00 00 00" (simplified)
            address = self.pm.pattern_scan_all(pattern)
            if address == 0 or address is None:
                return False, "Pattern not found in memory"
            
            final_address = address + offset
            return self.write_memory_value(final_address, value, size)
        except Exception as e:
            return False, str(e)

    def edit_savegame(self, file_path, search_key, new_value):
        """Generic savegame editor for JSON/XML/Text files."""
        if not os.path.exists(file_path):
            return False, "Save file not found"
        
        try:
            # Backup
            backup_path = file_path + ".bak"
            shutil.copy2(file_path, backup_path)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Simple regex replacement for the key
            # Matches "key":value or <key>value</key>
            pattern = rf'("{search_key}"\s*:\s*)([^,\"}}\s]+)' # JSON
            if not re.search(pattern, content):
                pattern = rf'(<{search_key}>)([^<]+)(</{search_key}>)' # XML
            
            new_content = re.sub(pattern, r'\1' + str(new_value) + r'\2' if '<' in pattern else r'\1' + str(new_value), content)
            
            if new_content == content:
                return False, "Value key not found in savegame"
                
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return True, "Savegame patched successfully"
        except Exception as e:
            return False, str(e)

    def detach(self):
        self.pm = None
        self.active_process = None
