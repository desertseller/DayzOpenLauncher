import sys
import os
import requests
import subprocess
import platform
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / "launcher.log"),
        logging.StreamHandler()
    ]
)

if getattr(sys, 'frozen', False):
    root_dir = os.path.dirname(sys.executable)
    internal_dir = os.path.join(root_dir, "_internal")
    if os.path.exists(internal_dir):
        sys.path.insert(0, internal_dir)
else:
    sys.path.insert(0, os.path.dirname(__file__))

from constants import VERSION
from version_utils import is_newer_version

def check_for_updates():
    repo = "PawelKawka/DayzOpenLauncher"
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        logging.info("Checking for updates...")
        response = requests.get(api_url, timeout=5)
        try:
            response.raise_for_status()
            data = response.json()
            latest_tag = data.get("tag_name", "").lstrip('v')

            if is_newer_version(latest_tag, VERSION):
                logging.info(f"New version available: {latest_tag}")
                return True, latest_tag
        finally:
            try:
                response.close()
            except Exception:
                pass
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while checking for updates: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while checking for updates: {e}")

    return False, None

if __name__ == "__main__":
    from start import DayZLauncherTUI
    tui = DayZLauncherTUI()
    tui.run()
