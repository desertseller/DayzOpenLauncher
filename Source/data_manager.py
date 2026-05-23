import time
import threading
from config import Config
from server_browser import ServerBrowser


class DataManager:
    def __init__(self):
        self.config = Config()
        self.browser = ServerBrowser()
        self.all_servers = []
        self.last_good_servers = []
        self.filtered_servers = []
        self.favrecent_recent = []
        self.favrecent_favorites = []
        self.live_info = {}
        self.last_search_text = ""
        self.last_fetch_ts = 0.0
        self.loading = True
        self.live_info_lock = threading.Lock()

#helpers

    def _build_lookup_cache(self):
        return {
            f"{s.get('ip')}:{s.get('port')}": s for s in self.all_servers
        } if self.all_servers else {}

    def _enrich_servers(self, source):
        enriched = []
        if not hasattr(self, '_lookup_cache') or self._lookup_cache.get('ts') != self.last_fetch_ts:
            self._lookup_cache = {
                'ts': self.last_fetch_ts,
                'data': self._build_lookup_cache()
            }
        global_lookup = self._lookup_cache['data']

        with self.live_info_lock:
            live_info_local = dict(self.live_info)

        for server in source:
            ip = server.get('ip')
            port = server.get('port')
            key_str = f"{ip}:{port}"
            key_tuple = (ip, port)

            combined = server.copy()

            if key_str in global_lookup:
                live = global_lookup[key_str]
                combined.update({
                    'players': live.get('players'),
                    'max_players': live.get('max_players'),
                    'queue': live.get('queue'),
                    'time': live.get('time'),
                    'map': live.get('map'),
                    'mods': live.get('mods', [])
                })

            if key_tuple in live_info_local:
                live = live_info_local[key_tuple]
                for field in ['players', 'max_players', 'queue', 'time', 'map']:
                    val = live.get(field)
                    if val is not None and val != '?':
                        combined[field] = val
                if live.get('mods'):
                    combined['mods'] = live['mods']

            enriched.append(combined)
        return enriched

    def _apply_filters(self, source, query):
        if not query:
            return list(source)
        query = query.lower()
        return [
            s for s in source
            if query in s.get('name', '').lower() or query in str(s.get('ip', ''))
        ]

    def _get_player_count(self, server):
        key = (server.get('ip'), server.get('port'))
        with self.live_info_lock:
            if key in self.live_info:
                p = self.live_info[key].get('players', 0)
            else:
                p = server.get('players', 0)
        try:
            return int(p)
        except (ValueError, TypeError):
            return 0

    def fetch_data(self, search_text=None, force=False):
        self.loading = True
        with self.live_info_lock:
            self.live_info.clear()
        try:
            if search_text and len(search_text) >= 2:
                result = self.browser.fetch_global_servers(search_text=search_text, force=force)
                self.all_servers = result if result is not None else []
                self.last_search_text = search_text
            else:
                result = self.browser.fetch_global_servers(force=force)
                if result is not None:
                    self.all_servers = result
                    self.last_good_servers = result
                    self.last_fetch_ts = time.time()
                self.last_search_text = ""
        except Exception as e:
            print(f"Fetch error: {e}")
        finally:
            self.loading = False
        return self.all_servers

    def update_filtered(self, current_tab, search_text):
        if self.loading:
            return self.filtered_servers

        if current_tab == "FAVRECENT":
            return self._update_favrecent(search_text)

        return self._update_standard(current_tab, search_text)

    def _update_favrecent(self, search_text):
        recent_raw = self.config.get("recent_servers", [])
        fav_raw = self.config.get("servers", [])

        self.favrecent_recent = self._apply_filters(self._enrich_servers(recent_raw), search_text)
        self.favrecent_favorites = self._apply_filters(self._enrich_servers(fav_raw), search_text)

        self.favrecent_recent.sort(key=self._get_player_count, reverse=True)
        self.favrecent_favorites.sort(key=self._get_player_count, reverse=True)

        self.filtered_servers = []
        return self.filtered_servers

    def _update_standard(self, current_tab, search_text):
        tab_source_map = {
            "GLOBAL": self.all_servers,
            "FAVORITES": self.config.get("servers", []),
            "RECENT": self.config.get("recent_servers", []),
        }
        source = tab_source_map.get(current_tab, [])

        if current_tab in ("FAVORITES", "RECENT"):
            source = self._enrich_servers(source)

        self.filtered_servers = self._apply_filters(source, search_text)

        if current_tab == "GLOBAL" and not self.filtered_servers and self.last_good_servers:
            if source is not self.last_good_servers:
                self.filtered_servers = self._apply_filters(self.last_good_servers, search_text)

        self.filtered_servers.sort(key=self._get_player_count, reverse=True)
        return self.filtered_servers
