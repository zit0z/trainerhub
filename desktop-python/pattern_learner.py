"""Pattern learning system for SweetCheat.

Helps discover AOB (Array-of-Byte) patterns for any game by:
1. Reading memory at a found address.
2. Scanning for surrounding bytes and wildcarding offsets.
3. Storing candidate patterns to the cloud via the API.

Works on Windows with pymem. On Linux the module only provides stub helpers.
"""
import struct
from typing import List, Tuple, Optional

PYMEM_OK = False
try:
    import pymem
    import pymem.process
    PYMEM_OK = True
except Exception:
    pass


def read_bytes(handle, address: int, size: int) -> bytes:
    if PYMEM_OK:
        return pymem.memory.read_bytes(handle, address, size)
    return b''


def hexdump(data: bytes) -> str:
    return ' '.join(f'{b:02x}' for b in data)


def make_pattern(data: bytes, wildcard_positions: List[int]) -> str:
    """Build AOB pattern with ?? at wildcard positions."""
    out = []
    for i, b in enumerate(data):
        if i in wildcard_positions:
            out.append('??')
        else:
            out.append(f'{b:02x}')
    return ' '.join(out)


def generate_candidates(data: bytes, min_stable: int = 6, max_wildcards: int = 8) -> List[str]:
    """Generate candidate AOB patterns by wildcarding high/low bytes likely to change."""
    if len(data) < min_stable:
        return []
    candidates = []
    n = len(data)
    # Strategy: try wildcards around middle region, keep first/last bytes stable
    for wildcard_count in range(1, min(max_wildcards, n - min_stable) + 1):
        for start in range(min_stable, n - min_stable - wildcard_count + 1):
            positions = list(range(start, start + wildcard_count))
            cand = make_pattern(data, positions)
            if cand not in candidates:
                candidates.append(cand)
    return candidates


def find_pattern_in_process(handle, module_base: int, module_size: int, pattern: str) -> List[int]:
    if not PYMEM_OK:
        return []
    pattern_bytes = []
    mask = []
    for token in pattern.split():
        if token == '??':
            pattern_bytes.append(0)
            mask.append(False)
        else:
            pattern_bytes.append(int(token, 16))
            mask.append(True)

    results = []
    region = read_bytes(handle, module_base, min(module_size, 50_000_000))
    m = len(pattern_bytes)
    for i in range(len(region) - m + 1):
        match = True
        for j in range(m):
            if mask[j] and region[i + j] != pattern_bytes[j]:
                match = False
                break
        if match:
            results.append(module_base + i)
    return results


def learn_pattern(handle, pid: int, address: int, region_size: int = 64) -> dict:
    """Read bytes around address and propose patterns."""
    data = read_bytes(handle, address, region_size)
    if not data:
        return {'success': False, 'message': 'Konnte Speicher nicht lesen.'}
    candidates = generate_candidates(data)
    return {
        'success': True,
        'hex': hexdump(data),
        'candidates': candidates[:20],
        'address': hex(address),
    }


def test_pattern(handle, module_base: int, module_size: int, pattern: str) -> dict:
    addrs = find_pattern_in_process(handle, module_base, module_size, pattern)
    return {
        'success': len(addrs) == 1,
        'matches': len(addrs),
        'addresses': [hex(a) for a in addrs[:5]],
    }


def save_pattern_to_db(api_base: str, api_key: str, game_id: int, trainer_id: int,
                       game_version: str, pattern: str, offset: int, value_type: str, value: int) -> bool:
    """Send new pattern to the backend trainer_patterns endpoint."""
    import json
    try:
        import urllib.request
        url = f"{api_base}/trainer-patterns.php"
        body = json.dumps({
            'game_id': game_id,
            'trainer_id': trainer_id,
            'game_version': game_version,
            'pattern': pattern,
            'offset': offset,
            'value_type': value_type,
            'value': value,
        }).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST',
                                     headers={'Content-Type': 'application/json'})
        if api_key:
            req.add_header('Authorization', f'Bearer {api_key}')
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('success', False)
    except Exception:
        return False
