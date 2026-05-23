import a2s
import re
import json
import time
import requests
import struct
import io
from constants import DZSA_API_URL, DEFAULT_TIMEOUT, QUERY_PORT_OFFSET
from config import Config

class ServerBrowser:
    def __init__(self):
        self.api_url = DZSA_API_URL
        self.cached_servers = []
        self.cached_full_list = []
        self.session = requests.Session()

    def close(self):
        try:
            self.session.close()
        except:
            pass

    def fetch_global_servers(self, search_text=None, page_limit=None, force=False):
        search_text = (search_text or "").lower()
        
        if self.cached_full_list and not force:
             servers = self.cached_full_list
        else:
            try:
                response = self.session.get(self.api_url, timeout=DEFAULT_TIMEOUT * 3)
                try:
                    if response.status_code == 200:
                        data = response.json()
                        raw_list = data.get('result', data.get('dayz', []))
                        
                        if not raw_list and isinstance(data, list):
                             raw_list = data
                        
                        parsed_servers = []
                        for s in raw_list:
                             endpoint = s.get('endpoint', {})
                             name = s.get('name', 'Unknown Server')
                             ip = endpoint.get('ip', '0.0.0.0')
                             g_port = int(s.get('gamePort', 2302))
                             q_port = int(endpoint.get('port', g_port + QUERY_PORT_OFFSET)) 
                             map_name = s.get('map', 'Unknown')
                             players = int(s.get('players', 0))
                             max_players = int(s.get('maxPlayers', 0))
                             
                             mods = []
                             raw_mods = s.get('mods', [])
                             for m in raw_mods:
                                  mname = m.get('name', 'Unknown')
                                  mid = m.get('steamWorkshopId') or m.get('workshopId') or m.get('steamId')
                                  if mid:
                                       mods.append({
                                            "id": str(mid),
                                            "name": mname,
                                            "steamWorkshopId": str(mid)
                                       })
                             
                             parsed_servers.append({
                                "name": name,
                                "ip": ip,
                                "port": g_port,
                                "query_port": q_port,
                                "map": map_name,
                                "players": players,
                                "max_players": max_players,
                                "time": s.get('time', '?'),
                                "queue": 0,
                                "mods": mods,
                                "status": "Online"
                            })
                        
                        self.cached_full_list = parsed_servers
                        servers = parsed_servers
                    else:
                        return []
                finally:
                    try:
                        response.close()
                    except Exception:
                        pass
            except Exception as e:
                print(f"Error fetching DZSA servers: {e}")
                return []
        
        if search_text:
             filtered = [s for s in servers if search_text in s['name'].lower() or search_text in s['map'].lower() or search_text in s['ip']]
             return filtered[:300]
        
        servers.sort(key=lambda x: x.get('players', 0), reverse=True)
        return servers[:300]

    def query_server(self, ip, port, query_port=None):
        target_ports = []
        if query_port:
            target_ports.append(int(query_port))
        
        if int(port) not in target_ports:
            target_ports.append(int(port))
            
        potential_query_port = int(port) + QUERY_PORT_OFFSET
        if potential_query_port not in target_ports:
            target_ports.append(potential_query_port)

        status_info = {
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

        for target in target_ports:
            try:
                info = a2s.info((ip, target), timeout=DEFAULT_TIMEOUT)
                status_info = {
                    "name": info.server_name,
                    "players": info.player_count,
                    "max_players": info.max_players,
                    "ping": int(info.ping * 1000),
                    "map": info.map_name,
                    "time": self.get_time_from_tags(info.keywords),
                    "queue": self.get_queue_from_tags(info.keywords),
                    "status": "Online",
                    "query_port": target,
                    "mods": self.get_mods_from_rules(ip, target)
                }
                return status_info
            except Exception:
                continue

        return status_info

    def get_mods_from_rules(self, ip, port):
        try:
            rules = a2s.rules((ip, port), timeout=DEFAULT_TIMEOUT, encoding=None)
            
            mods = self._parse_dayz_binary(rules)
            if mods:
                return mods

            if b'mods' in rules:
                try:
                    data = rules[b'mods']
                    offset = 0
                    if len(data) > 0 and data[0] == 0x00:
                        offset += 1
                    
                    if offset < len(data):
                        count = data[offset]
                        offset += 1
                        
                        mods = []
                        for _ in range(count):
                            if offset + 5 > len(data): break
                            mod_id = struct.unpack('<I', data[offset:offset+4])[0]
                            offset += 4
                            name_len = data[offset]
                            offset += 1
                            if offset + name_len > len(data): break
                            name = data[offset:offset+name_len].decode('utf-8', errors='ignore')
                            offset += name_len
                            mods.append({
                                "id": str(mod_id),
                                "name": name,
                                "steamWorkshopId": str(mod_id)
                            })
                        if mods: return mods
                except Exception:
                    pass

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
        except Exception:
            return []

    def _parse_dayz_binary(self, rules_resp):
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
            if len(payload) < 4: return []
            
            protocol_ver = struct.unpack('<B', reader.read(1))[0]
            overflow = struct.unpack('<B', reader.read(1))[0]
            dlc_flags = struct.unpack('<H', reader.read(2))[0]
            
            dlc_count = bin(dlc_flags).count('1')
            reader.read(4 * dlc_count)
            
            mods_count_raw = reader.read(1)
            if not mods_count_raw: return []
            mods_count = struct.unpack('<B', mods_count_raw)[0]
            mods = []
            
            for _ in range(mods_count):
                reader.read(4)
                raw_len_raw = reader.read(1)
                if not raw_len_raw: break
                raw_len = struct.unpack('<B', raw_len_raw)[0]
                ws_id_len = raw_len & 0x0F
                ws_id_bytes = reader.read(ws_id_len)
                workshop_id = int.from_bytes(ws_id_bytes, 'little')
                name_len_raw = reader.read(1)
                if not name_len_raw: break
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

    def get_time_from_tags(self, tags):
        if not tags: return "?"
        match = re.search(r'([0-9]{2}:[0-9]{2})$', tags)
        if match: return match.group(1)
        match = re.search(r'(\d{1,2}:\d{2})', tags)
        if match: return match.group(1)
        return "?"

    def get_queue_from_tags(self, tags):
        if not tags: return "0"
        tags = str(tags).lower()
        match = re.search(r'(?:lqs|lq|queue)[:\s]*(\d+)', tags)
        if match:
            return match.group(1)
        return "0"
