import struct
import io
import re

from constants import QUERY_PORT_OFFSET


def parse_mods_from_rules(ip, port, rules):
    mods = _parse_dayz_binary(rules)
    if mods:
        return mods

    mods = _parse_mods_blob(rules)
    if mods:
        return mods

    return _parse_mod_keys(rules)


def _parse_mods_blob(rules):
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


def _parse_mod_keys(rules):
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
