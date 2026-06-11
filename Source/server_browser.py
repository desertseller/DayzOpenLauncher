import a2s
import time
import requests
from constants import DZSA_API_URL, DEFAULT_TIMEOUT, QUERY_PORT_OFFSET
from mod_parser import parse_mods_from_rules
from tag_parser import get_time_from_tags, get_queue_from_tags


class ServerBrowser:
    def __init__(self):
        self.api_url = DZSA_API_URL
        self.cached_servers = []
        self.cached_full_list = []
        self.session = requests.Session()

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass

    def fetch_global_servers(self, search_text=None, page_limit=None, force=False):
        search_text = (search_text or "").lower()

        if self.cached_full_list and not force:
            servers = self.cached_full_list
        else:
            servers = self._fetch_from_api()
            if servers is None:
                return []

        if search_text:
            filtered = [
                s for s in servers
                if (search_text in s['name'].lower()
                    or search_text in s['map'].lower()
                    or search_text in s['ip'])
            ]
            return filtered[:300]

        servers.sort(key=lambda x: x.get('players', 0), reverse=True)
        return servers[:300]

    def _fetch_from_api(self):
        try:
            response = self.session.get(self.api_url, timeout=DEFAULT_TIMEOUT * 3)
            try:
                if response.status_code == 200:
                    data = response.json()
                    raw_list = data.get('result', data.get('dayz', []))
                    if not raw_list and isinstance(data, list):
                        raw_list = data

                    parsed = [self._parse_server_entry(s) for s in raw_list]
                    self.cached_full_list = parsed
                    return parsed
                return None
            finally:
                try:
                    response.close()
                except Exception:
                    pass
        except Exception as e:
            print(f"Error fetching API: {e}")
            return None

    @staticmethod
    def _parse_server_entry(raw):
        endpoint = raw.get('endpoint', {})
        name = raw.get('name', 'Unknown Server')
        ip = endpoint.get('ip', '0.0.0.0')
        try:
            g_port = int(raw.get('gamePort', 2302))
        except (ValueError, TypeError):
            g_port = 2302
        try:
            q_port = int(endpoint.get('port', g_port + QUERY_PORT_OFFSET))
        except (ValueError, TypeError):
            q_port = g_port + QUERY_PORT_OFFSET
        map_name = raw.get('map', 'Unknown')
        try:
            players = int(raw.get('players', 0))
        except (ValueError, TypeError):
            players = 0
        try:
            max_players = int(raw.get('maxPlayers', 0))
        except (ValueError, TypeError):
            max_players = 0

        mods = []
        for m in raw.get('mods', []):
            mname = m.get('name', 'Unknown')
            mid = m.get('steamWorkshopId') or m.get('workshopId') or m.get('steamId')
            if mid:
                mods.append({
                    "id": str(mid),
                    "name": mname,
                    "steamWorkshopId": str(mid)
                })

        return {
            "name": name,
            "ip": ip,
            "port": g_port,
            "query_port": q_port,
            "map": map_name,
            "players": players,
            "max_players": max_players,
            "time": raw.get('time', '?'),
            "queue": 0,
            "mods": mods,
            "status": "Online"
        }


    def query_server(self, ip, port, query_port=None):
        target_ports = self._build_target_ports(port, query_port)
        status_info = self._default_status()

        for target in target_ports:
            try:
                info = a2s.info((ip, target), timeout=DEFAULT_TIMEOUT)
                return self._status_from_info(info, ip, target)
            except Exception:
                continue

        return status_info

    @staticmethod
    def _build_target_ports(port, query_port=None):
        ports = []
        if query_port:
            ports.append(int(query_port))
        if int(port) not in ports:
            ports.append(int(port))
        potential = int(port) + QUERY_PORT_OFFSET
        if potential not in ports:
            ports.append(potential)
        return ports

    @staticmethod
    def _default_status():
        return {
            "name": "Unknown",
            "players": "?",
            "max_players": "?",
            "ping": "?",
            "map": "?",
            "time": "?",
            "queue": "?",
            "status": "Offline",
            "error": "No connection"
        }

    def _status_from_info(self, info, ip, query_port):
        return {
            "name": info.server_name,
            "players": info.player_count,
            "max_players": info.max_players,
            "ping": int(info.ping * 1000),
            "map": info.map_name,
            "time": get_time_from_tags(info.keywords),
            "queue": get_queue_from_tags(info.keywords),
            "status": "Online",
            "query_port": query_port,
            "mods": self.get_mods_from_rules(ip, query_port)
        }

    def get_mods_from_rules(self, ip, port):
        try:
            rules = a2s.rules((ip, port), timeout=DEFAULT_TIMEOUT, encoding=None)
        except Exception:
            return []
        return parse_mods_from_rules(ip, port, rules)
