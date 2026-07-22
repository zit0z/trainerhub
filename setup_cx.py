import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["tkinter", "requests", "urllib3", "email", "idna", "charset_normalizer", "pymem", "ctypes", "json", "xml.etree.ElementTree", "gzip", "shutil", "zipfile", "tempfile", "sdv_savegame", "savegame_trainers", "pattern_learner", "stardew_bridge"],
    "includes": ["tkinter.filedialog", "tkinter.messagebox", "tkinter.simpledialog", "tkinter.ttk", "tkinter.scrolledtext", "_tkinter", "win32api", "win32process", "win32gui", "win32con"],
    "excludes": ["matplotlib", "numpy", "pandas", "scipy", "PIL", "PyQt5", "PyQt6", "PySide2", "PySide6", "unittest", "test", "pydoc", "pdb", "tkinter.test", "_pytest", "pytest", "flask", "django", "boto3", "botocore", "setuptools", "pkg_resources"],
    "optimize": 2,
}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

executables = [
    Executable("main.py", base=base, target_name="SweetCheat.exe", icon=None)
]

setup(
    name="SweetCheat",
    version="0.3.5",
    description="SweetCheat Desktop App",
    options={"build_exe": build_exe_options},
    executables=executables,
)
