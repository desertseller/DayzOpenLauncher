import a2s
import re
import json
import time
import requests
import struct
import io
from constants import DZSA_API_URL, DEFAULT_TIMEOUT, QUERY_PORT_OFFSET


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
        g_port = int(raw.get('gamePort', 2302))
        q_port = int(endpoint.get('port', g_port + QUERY_PORT_OFFSET))
        map_name = raw.get('map', 'Unknown')
        players = int(raw.get('players', 0))
        max_players = int(raw.get('maxPlayers', 0))

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
            "time": self.get_time_from_tags(info.keywords),
            "queue": self.get_queue_from_tags(info.keywords),
            "status": "Online",
            "query_port": query_port,
            "mods": self.get_mods_from_rules(ip, query_port)
        }

    # ── Mod parsing from rules ───────────────────────────────────

    def get_mods_from_rules(self, ip, port):
        try:
            rules = a2s.rules((ip, port), timeout=DEFAULT_TIMEOUT, encoding=None)
        except Exception:
            return []

        mods = self._parse_dayz_binary(rules)
        if mods:
            return mods

        mods = self._parse_mods_blob(rules)
        if mods:
            return mods

        return self._parse_mod_keys(rules)

    def _parse_mods_blob(self, rules):
        if b'mods' not in rules:
            return []
        try:
            data = rules[b'mods']
            offset = 1 if (len(data) > 0 and data[0] == 0x00) else 0
            if offset >= len(data):
                return []

            count = data[offset]
            offset += 1
            mods = []
            for _ in range(count):
                if offset + 5 > len(data):
                    break
                mod_id = struct.unpack('<I', data[offset:offset + 4])[0]
                offset += 4
                name_len = data[offset]
                offset += 1
                if offset + name_len > len(data):
                    break
                name = data[offset:offset + name_len].decode('utf-8', errors='ignore')
                offset += name_len
                mods.append({
                    "id": str(mod_id),
                    "name": name,
                    "steamWorkshopId": str(mod_id)
                })
            return mods
        except Exception:
            return []

    def _parse_mod_keys(self, rules):
        mods = []
        i = 0
        while True:
            name_key = f"modName_{i}".encode('ascii')
            id_key = f"modId_{i}".encode('ascii')
            if name_key not in rules:
                break
            try:
                mid = rules.get(id_key, b"").decode('utf-8', errors='ignore')
                name = rules.get(name_key, b"Unknown").decode('utf-8', errors='ignore')
                if mid:
                    mods.append({
                        "id": mid,
                        "name": name,
                        "steamWorkshopId": mid
                    })
            except Exception:
                pass
            i += 1
        return mods

    # ── DayZ binary payload parser ─────────────────────────────────

    @staticmethod
    def _parse_dayz_binary(rules_resp):
        try:
            parts = []
            for key, value in rules_resp.items():
                if len(key) == 2:
                    seq = int.from_bytes(key, 'little')
                    parts.append((seq, value))

            if not parts:
                return []

            parts.sort(key=lambda x: x[0])
            payload = b"".join(p[1] for p in parts)

            payload = payload.replace(b"\x01\x02", b"\x00") \
                             .replace(b"\x01\x03", b"\xFF") \
                             .replace(b"\x01\x01", b"\x01")

            reader = io.BytesIO(payload)
            if len(payload) < 4:
                return []

            struct.unpack('<B', reader.read(1))[0]
            struct.unpack('<B', reader.read(1))[0]
            dlc_flags = struct.unpack('<H', reader.read(2))[0]

            dlc_count = bin(dlc_flags).count('1')
            reader.read(4 * dlc_count)

            mods_count_raw = reader.read(1)
            if not mods_count_raw:
                return []
            mods_count = struct.unpack('<B', mods_count_raw)[0]
            mods = []

            for _ in range(mods_count):
                reader.read(4)
                raw_len_raw = reader.read(1)
                if not raw_len_raw:
                    break
                raw_len = struct.unpack('<B', raw_len_raw)[0]
                ws_id_len = raw_len & 0x0F
                ws_id_bytes = reader.read(ws_id_len)
                workshop_id = int.from_bytes(ws_id_bytes, 'little')
                name_len_raw = reader.read(1)
                if not name_len_raw:
                    break
                name_len = struct.unpack('<B', name_len_raw)[0]
                name = reader.read(name_len).decode('utf-8', errors='replace')
                mods.append({
                    "id": str(workshop_id),
                    "name": name,
                    "steamWorkshopId": str(workshop_id)
                })
            return mods
        except Exception:
            return []

    # ── Tag helpers ──────────────────────────────────────────────

    @staticmethod
    def get_time_from_tags(tags):
        if not tags:
            return "?"
        match = re.search(r'([0-9]{2}:[0-9]{2})$', tags)
        if match:
            return match.group(1)
        match = re.search(r'(\d{1,2}:\d{2})', tags)
        if match:
            return match.group(1)
        return "?"

    @staticmethod
    def get_queue_from_tags(tags):
        if not tags:
            return "0"
        tags = str(tags).lower()
        match = re.search(r'(?:lqs|lq|queue)[:\s]*(\d+)', tags)
        if match:
            return match.group(1)
        return "0"
