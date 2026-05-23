import json
import os
import platform
import threading
from constants import CONFIG_FILE_NAME, DEFAULT_PROFILE_NAME, APP_NAME

class Config:
    def __init__(self, config_file=None):
        if config_file is None:
            self.config_dir = self._get_config_dir()
            self.config_file = os.path.join(self.config_dir, CONFIG_FILE_NAME)
        else:
            self.config_file = config_file
            self.config_dir = os.path.dirname(self.config_file)
        os.makedirs(self.config_dir, exist_ok=True)
        self._lock = threading.Lock()
        self.data = {
            "servers": [],
            "recent_servers": [],
            "dayz_path": "",
            "profile_name": DEFAULT_PROFILE_NAME
        }
        self.load()

    def _get_config_dir(self):
        if platform.system() == "Windows":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return os.path.join(appdata, APP_NAME)
        
        return os.path.join(os.path.expanduser("~"), APP_NAME)

    def load(self):
        with self._lock:
            if os.path.exists(self.config_file):
                try:
                    with open(self.config_file, "r") as f:
                        loaded = json.load(f)
                        for key, value in self.data.items():
                            if key in loaded:
                                self.data[key] = loaded[key]
                except Exception as e:
                    print(f"Error loading config: {e}")

    def save(self):
        with self._lock:
            try:
                with open(self.config_file, "w") as f:
                    json.dump(self.data, f, indent=4)
            except Exception as e:
                print(f"Error saving config: {e}")

    def get(self, key, default=None):
        val = self.data.get(key, default)
        if val is None:
            return default
        return val

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def add_server(self, name, ip, port, query_port=None):
        self.data["servers"].append({
            "name": name, 
            "ip": ip, 
            "port": port,
            "query_port": query_port or port 
        })
        self.save()

    def remove_server(self, index):
        if 0 <= index < len(self.data["servers"]):
            self.data["servers"].pop(index)
            self.save()
