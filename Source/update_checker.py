import threading
import time
import requests
from constants import VERSION, GITHUB_REPO
from version_utils import is_newer_version


def fetch_latest_version():
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        response = requests.get(api_url, timeout=5)
        try:
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "")
                latest_ver = latest_tag.lstrip('v')
                if is_newer_version(latest_ver, VERSION):
                    return latest_tag
        finally:
            try:
                response.close()
            except Exception:
                pass
    except Exception:
        pass
    return None


class UpdateChecker:
    def __init__(self, tui_app):
        self.tui = tui_app
        self.is_checking = False

    def start_check(self):
        if self.is_checking:
            return
            
        def _check():
            self.is_checking = True
            try:
                time.sleep(3)
                latest_tag = fetch_latest_version()
                if latest_tag:
                    self.tui.latest_update_info = {"tag": latest_tag}
                    if hasattr(self.tui, 'app'):
                        self.tui.app.invalidate()
            except Exception:
                pass
            finally:
                self.is_checking = False

        threading.Thread(target=_check, daemon=True).start()
