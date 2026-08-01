import os
import shutil
import subprocess
import sys

# THE ULTIMATE ANCHOR
ANCHOR = "SLA_SAYFE_ABSOLUTE_ZERO_0.9.14_FINAL"

def clean_caches():
    print("--- Clearing ALL PyInstaller Caches ---")
    paths_to_clean = [
        "build",
        "dist",
        os.path.expanduser("~/.cache/pip"),
    ]
    # Windows specific caches
    if os.name == 'nt':
        appdata = os.getenv('LOCALAPPDATA')
        if appdata:
            paths_to_clean.append(os.path.join(appdata, "pyinstaller"))

    for path in paths_to_clean:
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"Deleted: {path}")
        except Exception as e:
            print(f"Could not delete {path}: {e}")

def build():
    clean_caches()
    
    # Ensure the anchor is actually in the source
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()
    if ANCHOR not in content:
        print("Adding anchor to main.py...")
        with open("main.py", "w", encoding="utf-8") as f:
            f.write(f"# {ANCHOR}\n" + content)

    print("--- Starting PyInstaller Build ---")
    cmd = [
        "python", "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--clean",
        "--name", "SweetCheat_Slayer_Final",
        "main.py"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Build Failed: {result.stderr}")
        sys.exit(1)
    
    exe_path = "dist/SweetCheat_Slayer_Final.exe"
    if not os.path.exists(exe_path):
        print(f"Error: EXE not found at {exe_path}")
        sys.exit(1)
        
    with open(exe_path, "rb") as f:
        binary_data = f.read()
        if ANCHOR.encode() in binary_data:
            print("Slayer-Verification: SUCCESS! Binary is truly new.")
        else:
            print("Slayer-Verification: FAILED! Ghost binary detected again!")
            sys.exit(1)

if __name__ == "__main__":
    build()
