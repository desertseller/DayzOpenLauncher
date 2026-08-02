import os
import re
import sys
import fcntl
import subprocess


def setup_env():
    sys.stdout.write("\x1b]2;DayzOpenLauncher\x07")
    sys.stdout.flush()


def get_steam_path():
    paths = [
        os.path.expanduser("~/.local/share/Steam"),
        os.path.expanduser("~/.steam/steam"),
        os.path.expanduser("~/.steam/debian-installation"),
        os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam"),
        os.path.expanduser("~/snap/steam/common/.local/share/Steam"),
    ]
    for p in paths:
        if p and os.path.exists(p):
            if os.path.exists(os.path.join(p, "steamapps")):
                return p
    return None


def get_dayz_path(steam_path):
    if not steam_path:
        return None

    default_path = os.path.join(steam_path, "steamapps", "common", "DayZ")
    if os.path.exists(default_path):
        return default_path

    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf_path):
        try:
            with open(vdf_path, "r", encoding="utf-8") as f:
                content = f.read()

            paths = re.findall(r'"path"\s+"([^"]+)"', content)
            for p in paths:
                dayz_candidate = os.path.join(p, "steamapps", "common", "DayZ")
                if os.path.exists(dayz_candidate):
                    return dayz_candidate
        except Exception:
            pass

    return None


def is_dayz_running():
    try:
        result = subprocess.run(
            ["pgrep", "-f", "DayZ_x64"],
            capture_output=True, text=True, timeout=5
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def acquire_single_instance():
    lock_path = "/tmp/DayzOpenLauncher.lock"
    try:
        lock_file = open(lock_path, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except OSError:
        print("DayzOpenLauncher is already running.")
        sys.exit(0)


def release_single_instance(lock_file):
    try:
        if lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
    except Exception:
        pass
