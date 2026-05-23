import threading
import time
import platform
import os
import webbrowser
import subprocess
from steam_helper import SteamHelper

if platform.system() == "Windows":
    try:
        from windows.launcher import launch_dayz
    except ImportError:
        def launch_dayz(*args): pass
else:
    def launch_dayz(*args): pass

class ServerActions:
    def __init__(self, config):
        self.config = config
        self.cancel_requested = False

    def toggle_favorite(self, server):
        if not server: return
        
        favs = self.config.get("servers", [])
        exists = False
        for i, f in enumerate(favs):
            if f.get('ip') == server.get('ip') and f.get('port') == server.get('port'):
                favs.pop(i)
                exists = True
                break
        
        if not exists:
            favs.append({
                "name": server.get('name'),
                "ip": server.get('ip'),
                "port": server.get('port'),
                "query_port": server.get('query_port', server.get('port')),
                "map": server.get('map'),
                "mods": server.get('mods', [])
            })
        self.config.set("servers", favs)

    def cancel_launch(self):
        self.cancel_requested = True

    def join_server(self, server, on_launch_start, on_launch_end):
        recent = self.config.get("recent_servers", [])
        recent = [r for r in recent if not (r.get('ip') == server.get('ip') and r.get('port') == server.get('port'))]
        recent.insert(0, {
            "name": server.get('name'),
            "ip": server.get('ip'),
            "port": server.get('port'),
            "query_port": server.get('query_port', server.get('port')),
            "map": server.get('map'),
            "mods": server.get('mods', [])
        })
        self.config.set("recent_servers", recent[:20])
        
        dayz_path = self.config.get("dayz_path")
        if not dayz_path:
             on_launch_start("Error: DayZ path not set in Settings!")
             return
        
        # dir
        if os.path.isfile(dayz_path):
             dayz_path = os.path.dirname(dayz_path)

        profile = self.config.get("profile_name", "Survivor")
        
        workshop_path = os.path.abspath(os.path.join(dayz_path, "..", "..", "workshop", "content", "221100"))

        launch_message = f"Starting DayZ...\nIP: {server.get('ip')}:{server.get('port')}"
        on_launch_start(launch_message)
        self.cancel_requested = False
        
        def do_launch():
            try:
                steam = SteamHelper()
                # init steam
                steam_ready = steam.init()
                
                missing_or_pending = []
                final_mod_list = []

                if server.get('mods'):
                     for m in server['mods']:
                        if self.cancel_requested: return
                        mid = m.get('steamWorkshopId') or m.get('id')
                        try:
                            mid = str(int(mid))
                        except:
                            mid = None
                        
                        if mid:
                            mod_dir = os.path.join(workshop_path, mid)
                            
                            try:
                                is_downloaded = os.path.exists(mod_dir) and os.listdir(mod_dir)
                            except (OSError, PermissionError):
                                is_downloaded = False
                            if not is_downloaded:
                                 missing_or_pending.append(mid)
                            
                            final_mod_list.append(mod_dir)
                
                if missing_or_pending:
                     # log 1
                     if steam_ready and not self.cancel_requested:
                         on_launch_start(f"Downloading {len(missing_or_pending)} mods via Steam API...")
                         for mid in missing_or_pending:
                             steam.subscribe_mod(mid)
                     
                     start_wait = time.time()
                     last_missing_count = len(missing_or_pending)
                     currently_opening = None
                     
                     while True:
                         if self.cancel_requested:
                             on_launch_end(False, "Canceled by user.")
                             return

                         # check timeout
                         if time.time() - start_wait > 600:
                             if not self.cancel_requested:
                                 on_launch_start("Download timeout! Check Steam.")
                             break
                         
                         still_missing = []
                         for mid in missing_or_pending:
                             mod_dir = os.path.join(workshop_path, mid)
                             try:
                                 disk_exists = os.path.exists(mod_dir) and len(os.listdir(mod_dir)) > 0
                             except (OSError, PermissionError):
                                 disk_exists = False
                             steam_installed = steam.is_mod_installed(mid) if steam_ready else False
                             
                             if not (disk_exists or steam_installed):
                                 still_missing.append(mid)
                         
                         if not still_missing:
                             on_launch_start("All mods verified! Launching game...")
                             break
                         
                         if currently_opening not in still_missing:
                              currently_opening = still_missing[0]
                              on_launch_start(f"Waiting for mod: {currently_opening}\nOpening Workshop page...")
                              
                              steam_url = f"steam://url/CommunityFilePage/{currently_opening}"
                              web_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={currently_opening}"
                              
                              try:
                                   if platform.system() == "Windows":
                                        os.startfile(steam_url)
                                   time.sleep(0.5)
                              except:
                                   try: webbrowser.open(web_url)
                                   except: pass

                         on_launch_start(f"MOD DOWNLOAD IN PROGRESS... [ESC to Cancel]\nRemaining: {len(still_missing)} mods\nCurrently waiting for ID: {currently_opening}")
                         time.sleep(1.5)
                
                if self.cancel_requested: return
                
                final_check_missing = []
                final_mod_paths = []
                if server.get('mods'):
                     for m in server['mods']:
                        mid = m.get('steamWorkshopId') or m.get('id')
                        try:
                            mid_str = str(int(mid))
                            mod_path = os.path.join(workshop_path, mid_str)
                            if not os.path.exists(mod_path) or not os.listdir(mod_path):
                                 final_check_missing.append(mid_str)
                            else:
                                 final_mod_paths.append(mod_path)
                        except:
                            pass
                
                if final_check_missing:
                    on_launch_end(False, f"ERROR: Mods not found! {len(final_check_missing)} rem.")
                    return

                if self.cancel_requested: return
                success = launch_dayz(dayz_path, server.get('ip'), server.get('port'), profile, final_mod_paths)
                time.sleep(2)
                if not success:
                     on_launch_end(False, "Failed to start DayZ.")
                else:
                     on_launch_end(True, None)
            except Exception as e:
                on_launch_end(False, f"Error: {str(e)}")

        threading.Thread(target=do_launch, daemon=True).start()
