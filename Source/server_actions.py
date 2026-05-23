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
        def launch_dayz(*args):
            pass
else:
    def launch_dayz(*args):
        pass


class ServerActions:
    def __init__(self, config):
        self.config = config
        self.cancel_requested = False

#favorites mngt

    def toggle_favorite(self, server):
        if not server:
            return

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

    def _add_to_recent(self, server):
        recent = self.config.get("recent_servers", [])
        recent = [
            r for r in recent
            if not (r.get('ip') == server.get('ip') and r.get('port') == server.get('port'))
        ]
        recent.insert(0, {
            "name": server.get('name'),
            "ip": server.get('ip'),
            "port": server.get('port'),
            "query_port": server.get('query_port', server.get('port')),
            "map": server.get('map'),
            "mods": server.get('mods', [])
        })
        self.config.set("recent_servers", recent[:20])

    def _resolve_workshop_path(self, dayz_path):
        return os.path.abspath(os.path.join(dayz_path, "..", "..", "workshop", "content", "221100"))

    def _extract_mod_id(self, mod_entry):
        raw = mod_entry.get('steamWorkshopId') or mod_entry.get('id')
        try:
            return str(int(raw))
        except (ValueError, TypeError):
            return None

    def _is_mod_on_disk(self, workshop_path, mod_id):
        mod_dir = os.path.join(workshop_path, mod_id)
        try:
            return os.path.exists(mod_dir) and os.listdir(mod_dir)
        except (OSError, PermissionError):
            return False

    def _build_mod_lists(self, server, workshop_path):
        missing = []
        paths = []
        if not server.get('mods'):
            return missing, paths

        for m in server['mods']:
            if self.cancel_requested:
                return missing, paths
            mid = self._extract_mod_id(m)
            if not mid:
                continue
            if not self._is_mod_on_disk(workshop_path, mid):
                missing.append(mid)
            paths.append(os.path.join(workshop_path, mid))
        return missing, paths

    def _wait_for_mod_downloads(self, steam, missing, workshop_path, on_start, on_end):
        start_wait = time.time()
        currently_opening = None

        while True:
            if self.cancel_requested:
                on_end(False, "Canceled by user.")
                return False

            if time.time() - start_wait > 600:
                if not self.cancel_requested:
                    on_start("Download timeout! Check Steam.")
                break

            still_missing = []
            for mid in missing:
                disk = self._is_mod_on_disk(workshop_path, mid)
                steam_ok = steam.is_mod_installed(mid) if steam.initialized else False
                if not (disk or steam_ok):
                    still_missing.append(mid)

            if not still_missing:
                on_start("All mods verified! Launching game...")
                break

            if currently_opening not in still_missing:
                currently_opening = still_missing[0]
                on_start(f"Waiting for mod: {currently_opening}\nOpening Workshop page...")
                self._open_workshop_page(currently_opening)

            on_start(
                f"MOD DOWNLOAD IN PROGRESS... [ESC to Cancel]\n"
                f"Remaining: {len(still_missing)} mods\n"
                f"Currently waiting for ID: {currently_opening}"
            )
            time.sleep(1.5)

        return True

    def _open_workshop_page(self, mod_id):
        steam_url = f"steam://url/CommunityFilePage/{mod_id}"
        web_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        try:
            if platform.system() == "Windows":
                os.startfile(steam_url)
            time.sleep(0.5)
        except Exception:
            try:
                webbrowser.open(web_url)
            except Exception:
                pass

    def _final_mod_validation(self, server, workshop_path):
        missing = []
        paths = []
        if not server.get('mods'):
            return missing, paths

        for m in server['mods']:
            mid = self._extract_mod_id(m)
            if not mid:
                continue
            mod_path = os.path.join(workshop_path, mid)
            if not self._is_mod_on_disk(workshop_path, mid):
                missing.append(mid)
            else:
                paths.append(mod_path)
        return missing, paths

    def join_server(self, server, on_launch_start, on_launch_end):
        self._add_to_recent(server)

        dayz_path = self.config.get("dayz_path")
        if not dayz_path:
            on_launch_start("Error: DayZ path not set in Settings!")
            return

        if os.path.isfile(dayz_path):
            dayz_path = os.path.dirname(dayz_path)

        profile = self.config.get("profile_name", "Survivor")
        workshop_path = self._resolve_workshop_path(dayz_path)

        on_launch_start(f"Starting DayZ...\nIP: {server.get('ip')}:{server.get('port')}")
        self.cancel_requested = False

        def do_launch():
            try:
                steam = SteamHelper()
                steam_ready = steam.init()

                missing, mod_paths = self._build_mod_lists(server, workshop_path)

                if missing:
                    if steam_ready and not self.cancel_requested:
                        on_launch_start(f"Downloading {len(missing)} mods via Steam API...")
                        for mid in missing:
                            steam.subscribe_mod(mid)

                    ok = self._wait_for_mod_downloads(steam, missing, workshop_path, on_launch_start, on_launch_end)
                    if not ok:
                        return

                if self.cancel_requested:
                    return

                final_missing, final_paths = self._final_mod_validation(server, workshop_path)
                if final_missing:
                    on_launch_end(False, f"ERROR: Mods not found! {len(final_missing)} rem.")
                    return

                if self.cancel_requested:
                    return

                success = launch_dayz(
                    dayz_path,
                    server.get('ip'),
                    server.get('port'),
                    profile,
                    final_paths
                )
                time.sleep(2)
                if not success:
                    on_launch_end(False, "Failed to start DayZ.")
                else:
                    on_launch_end(True, None)
            except Exception as e:
                on_launch_end(False, f"Error: {str(e)}")

        threading.Thread(target=do_launch, daemon=True).start()
