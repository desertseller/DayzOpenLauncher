import time
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

    def _enrich_servers(self, source):
        enriched = []
        if not hasattr(self, '_lookup_cache') or self._lookup_cache.get('ts') != self.last_fetch_ts:
             self._lookup_cache = {
                 'ts': self.last_fetch_ts,
                 'data': {f"{s.get('ip')}:{s.get('port')}": s for s in self.all_servers} if self.all_servers else {}
             }
        global_lookup = self._lookup_cache['data']

        for s in source:
            key_str = f"{s.get('ip')}:{s.get('port')}"
            key_tuple = (s.get('ip'), s.get('port'))

            combined = s.copy()

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

            if key_tuple in self.live_info:
                live = self.live_info[key_tuple]
                for field in ['players', 'max_players', 'queue', 'time', 'map']:
                    val = live.get(field)
                    if val is not None and val != '?':
                         combined[field] = val

                if live.get('mods'):
                     combined['mods'] = live['mods']

            enriched.append(combined)
        return enriched

    def fetch_data(self, search_text=None, force=False):
        self.loading = True
        self.live_info.clear()
        try:
            if search_text and len(search_text) >= 2:
                result = self.browser.fetch_global_servers(search_text=search_text, force=force)
                self.all_servers = result if result is not None else []
                self.last_search_text = search_text
            else:
                result = self.browser.fetch_global_servers(force=force)
                if result:
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

        name_q = search_text.lower()

        def apply_filters(source):
            out = []
            for s in source:
                name = s.get('name', '').lower()
                ip = str(s.get('ip', ''))
                if not name_q or name_q in name or name_q in ip:
                    out.append(s)
            return out

        def get_player_count(server):
            key = (server.get('ip'), server.get('port'))
            if key in self.live_info:
                p = self.live_info[key].get('players', 0)
            else:
                p = server.get('players', 0)
            try:
                return int(p)
            except:
                return 0

        if current_tab == "FAVRECENT":
            recent_source = self.config.get("recent_servers", [])
            fav_source = self.config.get("servers", [])

            self.favrecent_recent = apply_filters(self._enrich_servers(recent_source))
            self.favrecent_favorites = apply_filters(self._enrich_servers(fav_source))

            self.favrecent_recent.sort(key=get_player_count, reverse=True)
            self.favrecent_favorites.sort(key=get_player_count, reverse=True)

            self.filtered_servers = []
            return self.filtered_servers

        if current_tab == "GLOBAL":
            source = self.all_servers
        elif current_tab == "FAVORITES":
            source = self.config.get("servers", [])
        elif current_tab == "RECENT":
            source = self.config.get("recent_servers", [])
        else:
            source = []

        if current_tab in ["FAVORITES", "RECENT"]:
            source = self._enrich_servers(source)

        self.filtered_servers = apply_filters(source)

        if current_tab == "GLOBAL" and not self.filtered_servers and self.last_good_servers:
            if source is not self.last_good_servers:
                self.filtered_servers = apply_filters(self.last_good_servers)

        self.filtered_servers.sort(key=get_player_count, reverse=True)
        return self.filtered_servers
