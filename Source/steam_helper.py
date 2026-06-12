import os
import sys
import time

try:
    from steamworks import STEAMWORKS
    from steamworks.enums import EItemState
except ImportError:
    STEAMWORKS = None
    EItemState = None

class SteamHelper:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SteamHelper, cls).__new__(cls)
            cls._instance._init_once()
        return cls._instance

    def _init_once(self):
        self.steam = None
        self.workshop = None
        self.initialized = False
        self._init_done = False

    def init(self):
        if getattr(self, '_init_done', False):
            return self.initialized
            
        self._init_done = True
        
        if not STEAMWORKS:
            return False
            
        if getattr(sys, 'frozen', False):
            root_dir = os.path.dirname(sys.executable)
        else:
            root_dir = os.path.dirname(os.path.abspath(__file__))
            if os.path.basename(root_dir) == "Source":
                root_dir = os.path.dirname(root_dir)
                
        os.environ['SteamAppId'] = '221100'
        os.environ['SteamGameId'] = '221100'
        
        try:
            self.steam = STEAMWORKS()
            self.steam.initialize()
            self.workshop = self.steam.Workshop
            self.initialized = True
            return True
        except Exception as e:
            return False

    def is_mod_installed(self, mod_id):
        if not self.initialized: return False
        try:
            state = self.workshop.GetItemState(int(mod_id))
            val = state.value if hasattr(state, 'value') else state
            return (val & 4) == 4
        except:
            return False

    def is_subscribed(self, mod_id):
        if not self.initialized: return False
        try:
            state = self.workshop.GetItemState(int(mod_id))
            val = state.value if hasattr(state, 'value') else state
            return (val & 1) == 1
        except:
            return False

    def subscribe_mod(self, mod_id):
        if not self.initialized: return
        try:
            self.workshop.SubscribeItem(int(mod_id))
        except:
            pass

