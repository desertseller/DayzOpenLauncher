import threading
import time
import requests
from constants import VERSION
from version_utils import is_newer_version

class UpdateChecker:
    def __init__(self, tui_app):
        self.tui = tui_app

    def start_check(self):
        def _check():
            try:
                time.sleep(3)

                response = requests.get(
                    "https://api.github.com/repos/PawelKawka/DayzOpenLauncher/releases/latest",
                    timeout=5
                )
                try:
                    if response.status_code == 200:
                        data = response.json()
                        latest_tag = data.get("tag_name", "")
                        latest_ver = latest_tag.lstrip('v')

                        if is_newer_version(latest_ver, VERSION):
                            self.tui.latest_update_info = {"tag": latest_tag}
                            if hasattr(self.tui, 'app'):
                                self.tui.app.invalidate()
                finally:
                    try:
                        response.close()
                    except Exception:
                        pass
            except Exception:
                pass

        threading.Thread(target=_check, daemon=True).start()
