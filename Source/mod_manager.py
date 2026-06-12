import os
import re
import io
import time
from rich.table import Table
from rich.console import Console
from rich import box
from prompt_toolkit.formatted_text import ANSI

from console_renderer import render_to_ansi, ping_color


class ModManager:
    def __init__(self, config):
        self.config = config
        self.cached_installed_mods = None
        self.mods_page = 0
        self._workshop_cache = set()
        self._workshop_cache_ts = 0.0

    def clear_cache(self):
        self.cached_installed_mods = None
        self._mods_cache_key = None
        if hasattr(self, '_cached_gb_size'):
            del self._cached_gb_size

    def _get_workshop_path(self):
        dayz_path = self.config.get("dayz_path")
        if not dayz_path:
            return None
        if os.path.isfile(dayz_path):
            dayz_path = os.path.dirname(dayz_path)
        return os.path.abspath(os.path.join(dayz_path, "..", "..", "workshop", "content", "221100"))

    @staticmethod
    def _extract_mod_workshop_id(mod_entry):
        raw = mod_entry.get('steamWorkshopId') or mod_entry.get('id')
        try:
            return str(int(raw))
        except (ValueError, TypeError):
            return None

    def _is_mod_installed(self, mod_id):
        workshop = self._get_workshop_path()
        if not workshop:
            return False

        now = time.time()
        if now - getattr(self, '_workshop_cache_ts', 0) > 10.0:
            try:
                self._workshop_cache = set(os.listdir(workshop))
            except Exception:
                self._workshop_cache = set()
            self._workshop_cache_ts = now

        return mod_id in self._workshop_cache

    def _get_mod_dir_size(self, mod_id):
        workshop = self._get_workshop_path()
        if not workshop:
            return 0
        mod_dir = os.path.join(workshop, mod_id)
        total = 0
        try:
            for dirpath, _, filenames in os.walk(mod_dir):
                for f in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, f))
                    except OSError:
                        pass
        except Exception:
            pass
        return total

    def _get_total_mods_size_gb(self):
        if hasattr(self, '_cached_gb_size'):
            return self._cached_gb_size
        workshop = self._get_workshop_path()
        if not workshop or not os.path.exists(workshop):
            return 0.0
        total = 0
        try:
            for entry in os.listdir(workshop):
                mod_path = os.path.join(workshop, entry)
                if os.path.isdir(mod_path):
                    total += self._get_mod_dir_size(entry)
        except Exception:
            pass
        self._cached_gb_size = total / (1024 ** 3)
        return self._cached_gb_size


    def get_mod_name(self, path):
        try:
            meta_path = os.path.join(path, "meta.cpp")
            if os.path.exists(meta_path):
                with open(meta_path, 'r', errors='ignore') as f:
                    content = f.read()
                    match = re.search(r'name\s*=\s*"(.*?)";', content)
                    if match:
                        return match.group(1)
        except Exception:
            pass
        return os.path.basename(path)

    def _format_last_played(self, server):
        timestamps = self.config.get("last_played_timestamps", {})
        key = f"{server.get('ip')}:{server.get('port')}"
        ts = timestamps.get(key)
        if not ts:
            return None
        diff = time.time() - ts
        if diff < 0:
            return None
        if diff < 60:
            return "just now"
        if diff < 3600:
            m = int(diff // 60)
            return f"{m} min ago" if m == 1 else f"{m} mins ago"
        if diff < 86400:
            h = int(diff // 3600)
            return f"{h} hr ago" if h == 1 else f"{h} hrs ago"
        d = int(diff // 86400)
        return f"{d} day ago" if d == 1 else f"{d} days ago"

    def get_mod_list_text(self, server, live_info_entry, available_height=None):
        def render(console):
            if server:
                map_name = (live_info_entry.get('map') if live_info_entry else None) or server.get('map', 'Unknown')
                console.print(f"[bold cyan]{server.get('name', 'Unknown')[:35]}[/bold cyan]")
                console.print(f"IP: {server.get('ip')}:{server.get('port')}")
                console.print(f"Map: {map_name}")
                last_played = self._format_last_played(server)
                if last_played:
                    console.print(f"[dim]Last played: {last_played}[/dim]")
                console.print("─" * 38, style="dim white")

            if live_info_entry:
                console.print("[bold yellow]LIVE INFO[/bold yellow]")
                ping = live_info_entry.get('ping', '?')
                ping_style = self._ping_style(ping)
                console.print(f"Players: {live_info_entry.get('players')}/{live_info_entry.get('max_players')}")
                console.print(f"Ping:    [{ping_style}]{ping} ms[/{ping_style}]")
                console.print(f"Queue:   [orange1]{live_info_entry.get('queue')}[/orange1]")
                console.print(f"Time:    {live_info_entry.get('time')}")
            elif server:
                console.print("[bold yellow]LIVE INFO[/bold yellow]")
                players = server.get('players', '0')
                max_players = server.get('max_players', '0')
                ping_style = self._ping_style('?')
                console.print(f"Players: {players}/{max_players}")
                console.print(f"Ping:    [{ping_style}]? ms[/{ping_style}]")
                queue = server.get('queue', '0')
                console.print(f"Queue:   [orange1]{queue}[/orange1]")
                time_val = server.get('time', '?')
                console.print(f"Time:    {time_val}")
            else:
                console.print("[dim]No live data available[/dim]")

            console.print("\n[bold yellow]MODS[/bold yellow]")
            mods = server.get('mods', []) if server else []
            if not mods and live_info_entry:
                mods = live_info_entry.get('mods', [])

            if mods:
                installed_count = 0
                missing_count = 0
                mod_status = []
                for m in mods:
                    mid = self._extract_mod_workshop_id(m)
                    installed = bool(mid and self._is_mod_installed(mid))
                    if installed:
                        installed_count += 1
                    else:
                        missing_count += 1
                    mod_status.append((m, installed))

                console.print(f"Total: {len(mods)} ([green]{installed_count} installed[/green] / [red]{missing_count} missing[/red])")

                max_show = len(mods)
                if available_height:
                    max_from_height = max(5, available_height - 20)
                    max_show = min(len(mods), max_from_height)

                for m, installed in mod_status[:max_show]:
                    mname = m.get('name', 'Unknown')
                    if len(mname) > 35:
                        mname = mname[:32] + "..."
                    if installed:
                        console.print(f"• [green]{mname}[/green]")
                    else:
                        console.print(f"• [red]{mname}[/red]")

                if len(mods) > max_show:
                    remaining = len(mods) - max_show
                    rem_installed = sum(1 for _, inst in mod_status[max_show:] if inst)
                    rem_missing = remaining - rem_installed
                    console.print(
                        f"  ... and [bold]{remaining} more[/bold] "
                        f"([green]{rem_installed}[/green]/[red]{rem_missing}[/red])"
                    )
            else:
                console.print("[dim]Vanilla / No mods listed[/dim]")

        return render_to_ansi(render, 38)

    @staticmethod
    def _ping_style(ping):
        return ping_color(ping)

    def get_installed_mods_text(self, width=80):
        cache_key = (self.mods_page, width)
        if (hasattr(self, '_mods_cache_key') and self._mods_cache_key == cache_key
                and self.cached_installed_mods):
            return self.cached_installed_mods

        dayz_path = self.config.get("dayz_path")
        if not dayz_path or not os.path.exists(dayz_path):
            return "DayZ path not set or invalid. Check Settings (F3)."

        try:
            mods = self._collect_installed_mods(dayz_path)

            if not mods:
                workshop = os.path.join(dayz_path, "!Workshop")
                return f"No mods found.\nChecked:\n- {dayz_path}\n- {workshop}\n\n:("

            result = self._render_mod_table(mods, width)
            self.cached_installed_mods = result
            self._mods_cache_key = cache_key
            return result
        except Exception as e:
            return f"Error reading mods: {e}"

    def _collect_installed_mods(self, dayz_path):
        mods = []
        paths_to_check = [dayz_path]
        workshop_path = os.path.join(dayz_path, "!Workshop")
        if os.path.exists(workshop_path):
            paths_to_check.append(workshop_path)

        for p in paths_to_check:
            for entry in os.listdir(p):
                if entry.startswith("@"):
                    full_path = os.path.join(p, entry)
                    mods.append((self.get_mod_name(full_path), entry))

        try:
            base_steam = os.path.dirname(os.path.dirname(dayz_path))
            sid_path = os.path.join(base_steam, "workshop", "content", "221100")
            if os.path.exists(sid_path):
                for sid in os.listdir(sid_path):
                    s_mod_path = os.path.join(sid_path, sid)
                    if os.path.isdir(s_mod_path):
                        mods.append((self.get_mod_name(s_mod_path), sid))
        except Exception:
            pass

        return mods

    def _render_mod_table(self, mods, width):
        unique_names = sorted({m[0] for m in mods}, key=lambda x: x.lower())
        total = len(unique_names)
        cols, rows = 3, 24
        per_page = cols * rows
        total_pages = max(1, (total + per_page - 1) // per_page)

        self.mods_page = max(0, min(self.mods_page, total_pages - 1))
        start = self.mods_page * per_page
        page_mods = unique_names[start:min(start + per_page, total)]

        total_gb = self._get_total_mods_size_gb()
        size_text = f" | [dim]{total_gb:.2f} GB[/dim]" if total_gb > 0 else ""
        header = f"[bold yellow]PAGE {self.mods_page + 1}/{total_pages}[/bold yellow] (Total: {total}){size_text}"
        table = Table(
            box=None, padding=(0, 1), expand=True,
            show_header=True, header_style="bold white",
            title=header, title_justify="left"
        )
        for _ in range(cols):
            table.add_column(
                "Mod Name", style="cyan", no_wrap=True,
                overflow="ellipsis", header_style="dim"
            )
        table.show_header = False

        for i in range(0, len(page_mods), cols):
            row = page_mods[i:i + cols]
            while len(row) < cols:
                row.append("")
            table.add_row(*row)

        from console_renderer import render_table_to_ansi
        return render_table_to_ansi(table, max(width, 80))
