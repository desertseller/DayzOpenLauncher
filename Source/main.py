import sys
import os
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
from update_checker import fetch_latest_version


def check_for_updates():
    try:
        logging.info("Checking for updates...")
        latest_tag = fetch_latest_version()
        if latest_tag:
            logging.info(f"New version available: {latest_tag}")
            return True, latest_tag
    except Exception as e:
        logging.error(f"Error while checking for updates: {e}")

    return False, None

if __name__ == "__main__":
    if platform.system() == "Windows":
        from windows.utils import acquire_single_instance, release_single_instance
    else:
        from linux.utils import acquire_single_instance, release_single_instance

    instance_handle = acquire_single_instance()
    try:
        from start import DayZLauncherTUI
        tui = DayZLauncherTUI()
        tui.run()
    finally:
        release_single_instance(instance_handle)
