# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['/var/www/trainerhub/desktop-python'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'ui_components', 'gui_module', 'updater', 'cheat_engine',
        'stardew_savegame', 'pattern_learner', 'savegame_trainers', 'sdv_savegame',
        'pymem', 'pymem.process', 'pymem.memory', 'pymem.ressources.structure', 'pymem.ressources.kernel32',
        'requests', 'requests.adapters', 'urllib3', 'urllib3.util.retry'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'numpy', 'pandas', 'tkinter.test',
        'unittest', 'distutils', 'xml', 'xmlrpc', 'html', 'mailbox',
        'colorsys', 'chunk', 'cryptography', 'pydoc', 'pydoc_data',
        'lib2to3', 'pkg_resources', 'setuptools', 'Cython', 'pytz', 'boto3'
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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    manifest=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TrainerHub',
)
