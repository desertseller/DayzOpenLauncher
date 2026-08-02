import winreg
import os
import re
import sys
import ctypes
import logging
import subprocess

MUTEX_NAME = "Global\\DayzOpenLauncher"

def setup_env():
    try:
        app_id = 'DayzOpenLauncher'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        ctypes.windll.kernel32.SetConsoleTitleW("DayzOpenLauncher")
    except Exception:
        pass

def get_steam_path():
    try:
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Valve\\Steam")
        steam_path = winreg.QueryValueEx(hkey, "SteamPath")[0]
        winreg.CloseKey(hkey)
        return steam_path
    except:
        return None

def parse_acf(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    match = re.search(r'"installdir"\s+"([^"]+)"', content)
    if match:
        return {"installdir": match.group(1)}
    return {}

def get_dayz_path(steam_path):
    if not steam_path:
        return None
    
    manifest = os.path.join(steam_path, "steamapps", "appmanifest_221100.acf")
    if os.path.exists(manifest):
        data = parse_acf(manifest)
        if "installdir" in data:
            return os.path.join(steam_path, "steamapps", "common", data["installdir"])
            
    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf_path):
        with open(vdf_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            paths = re.findall(r'"path"\s+"([^"]+)"', content)
            for lib_path in paths:
                lib_path = lib_path.replace("\\\\", "\\")
                manifest = os.path.join(lib_path, "steamapps", "appmanifest_221100.acf")
                if os.path.exists(manifest):
                     data = parse_acf(manifest)
                     if "installdir" in data:
                        return os.path.join(lib_path, "steamapps", "common", data["installdir"])
    return None

def is_dayz_running():
    try:
        result = subprocess.run(
            ['tasklist', '/fi', 'imagename eq DayZ_x64.exe'],
            capture_output=True, text=True, timeout=5
        )
        return 'DayZ_x64.exe' in result.stdout
    except Exception:
        return False

def acquire_single_instance():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.GetLastError() == 183:
        logging.warning("DayzOpenLauncher is already running.")
        ctypes.windll.kernel32.CloseHandle(mutex)
        sys.exit(0)
    return mutex

def release_single_instance(mutex):
    try:
        ctypes.windll.kernel32.CloseHandle(mutex)
    except Exception:
        pass
