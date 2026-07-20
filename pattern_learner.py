"""
Pattern Learner: Allows users to discover memory patterns themselves.
No copyrighted content - just a tool for scanning the user's own game memory.
"""
import time
import struct
from collections import defaultdict

try:
    import pymem
    from pymem import Pymem
    WINDOWS = True
except ImportError:
    WINDOWS = False

VALUE_SIZES = {'int8': 1, 'int16': 2, 'int32': 4, 'int64': 8, 'float': 4, 'double': 8}
VALUE_PACK = {
    'int8': 'b', 'int16': 'h', 'int32': 'i', 'int64': 'q',
    'float': 'f', 'double': 'd',
    'uint8': 'B', 'uint16': 'H', 'uint32': 'I', 'uint64': 'Q'
}

class PatternLearner:
    def __init__(self, pid):
        if not WINDOWS:
            raise RuntimeError("Pattern learning requires Windows + pymem")
        self.pm = Pymem(pid)
        self.scan_history = []
    
    def _read_value(self, addr, value_type):
        size = VALUE_SIZES.get(value_type, 4)
        try:
            data = self.pm.read_bytes(addr, size)
            return struct.unpack(VALUE_PACK.get(value_type, 'i'), data)[0]
        except Exception:
            return None
    
    def _write_value(self, addr, value, value_type):
        size = VALUE_SIZES.get(value_type, 4)
        try:
            packed = struct.pack(VALUE_PACK.get(value_type, 'i'), value)
            self.pm.write_bytes(addr, packed, size)
            return True
        except Exception:
            return False
    
    def _get_readable_regions(self):
        regions = []
        addr = 0
        while addr < 0x7FFF00000000:
            try:
                mbi = pymem.memory.virtual_query(self.pm.process_handle, addr)
                if mbi.State == 0x1000 and mbi.Protect in (0x04, 0x20, 0x40, 0x02):
                    regions.append((mbi.BaseAddress, mbi.BaseAddress + mbi.RegionSize))
                addr = mbi.BaseAddress + mbi.RegionSize
                if mbi.RegionSize == 0:
                    break
            except Exception:
                break
        return regions
    
    def first_scan(self, value, value_type='int32'):
        """Find all addresses matching the value."""
        results = []
        regions = self._get_readable_regions()
        for start, end in regions:
            size = end - start
            if size > 100_000_000:
                continue
            try:
                data = self.pm.read_bytes(start, size)
            except Exception:
                continue
            
            fmt = VALUE_PACK.get(value_type, 'i')
            step = VALUE_SIZES.get(value_type, 4)
            
            for i in range(0, len(data) - step, step):
                try:
                    v = struct.unpack(fmt, data[i:i+step])[0]
                    if v == value:
                        results.append(start + i)
                except Exception:
                    pass
        self.scan_history.append(results)
        return results
    
    def next_scan(self, value):
        """Filter previous results by new value."""
        if not self.scan_history:
            return []
        prev = self.scan_history[-1]
        results = []
        for addr in prev:
            v = self._read_value_from_any_type(addr)
            if v is not None and v == value:
                results.append(addr)
        self.scan_history.append(results)
        return results
    
    def _read_value_from_any_type(self, addr):
        for vt in ['int32', 'float', 'int64', 'int16', 'int8']:
            v = self._read_value(addr, vt)
            if v is not None:
                return v
        return None
    
    def generate_pattern(self, addr, radius=16):
        """Generate AOB pattern around address for future scans."""
        try:
            data = self.pm.read_bytes(addr - radius, radius * 2 + 8)
            # Convert to bytes with wildcards for dynamic bytes
            # Simple: output first 16 bytes as hex with optional wildcards
            pattern_bytes = data[:24]
            return ' '.join(f'{b:02X}' for b in pattern_bytes)
        except Exception as e:
            return f"error:{e}"
    
    def write_and_freeze(self, addr, value, value_type='int32', freeze=False):
        success = self._write_value(addr, value, value_type)
        if freeze and success:
            import threading
            def freeze_loop():
                while getattr(self, f'_freeze_{addr}', False):
                    self._write_value(addr, value, value_type)
                    time.sleep(0.5)
            setattr(self, f'_freeze_{addr}', True)
            threading.Thread(target=freeze_loop, daemon=True).start()
        return success
    
    def stop_freeze(self, addr):
        setattr(self, f'_freeze_{addr}', False)

