# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.simpledialog', 'tkinter.ttk',
        'tkinter.scrolledtext', '_tkinter', 'win32api', 'win32process', 'win32gui', 'win32con',
        'ctypes', 'json', 'xml.etree.ElementTree', 'gzip', 'shutil', 'zipfile', 'tempfile',
        'pymem', 'pymem.process', 'pymem.memory', 'urllib.request', 'urllib.error', 'http.client',
        'pkg_resources', 'setuptools'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'unittest', 'test', 'pydoc', 'pdb', 'tkinter.test', '_pytest', 'pytest', 'flask', 'django',
        'boto3', 'botocore'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TrainerHub',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='TrainerHub'
)
