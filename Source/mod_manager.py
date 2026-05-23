import os
import re
import io
from rich.table import Table
from rich.console import Console
from rich import box
from prompt_toolkit.formatted_text import ANSI

class ModManager:
    def __init__(self, config):
        self.config = config
        self.cached_installed_mods = None
        self.mods_page = 0

    def clear_cache(self):
        self.cached_installed_mods = None

    def get_mod_name(self, path):
        try:
            meta_path = os.path.join(path, "meta.cpp")
            if os.path.exists(meta_path):
                with open(meta_path, 'r', errors='ignore') as f:
                    content = f.read()
                    match = re.search(r'name\s*=\s*"(.*?)";', content)
                    if match:
                        return match.group(1)
        except:
            pass
        return os.path.basename(path)

    def get_mod_list_text(self, server, live_info_entry):
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, color_system="standard", width=38)
        
        if server:
            map_name = live_info_entry.get('map') if live_info_entry else server.get('map', 'Unknown')
            console.print(f"[bold cyan]{server.get('name', 'Unknown')[:35]}[/bold cyan]")
            console.print(f"IP: {server.get('ip')}:{server.get('port')}")
            console.print(f"Map: {map_name}")
            console.print("─" * 38, style="dim white")
        
        if live_info_entry:
            console.print("[bold yellow]LIVE INFO[/bold yellow]")
            
            ping = live_info_entry.get('ping', '?')
            ping_style = "white"
            if isinstance(ping, int):
                if ping <= 75: ping_style = "green"
                elif ping <= 150: ping_style = "yellow"
                else: ping_style = "red"

            console.print(f"Players: {live_info_entry.get('players')}/{live_info_entry.get('max_players')}")
            console.print(f"Ping:    [{ping_style}]{ping} ms[/{ping_style}]")
            console.print(f"Queue:   [orange1]{live_info_entry.get('queue')}[/orange1]")
            console.print(f"Time:    {live_info_entry.get('time')}")
        else:
            console.print("[dim]No live data available[/dim]")

        console.print("\n[bold yellow]MODS[/bold yellow]")
        mods = server.get('mods', []) if server else []
        if not mods and live_info_entry:
            mods = live_info_entry.get('mods', [])
            
        if mods:
            console.print(f"Total: {len(mods)}")
            for m in mods[:20]:
                mname = m.get('name', 'Unknown')
                if len(mname) > 35: mname = mname[:32] + "..."
                console.print(f"• [dim]{mname}[/dim]")
            if len(mods) > 20:
                console.print(f"  ... and {len(mods)-20} more")
        else:
            console.print("[dim]Vanilla / No mods listed[/dim]")
        
        result = ANSI(output.getvalue())
        try:
            output.close()
        except Exception:
            pass
        try:
            console.close()
        except Exception:
            pass
        return result

    def get_installed_mods_text(self, width=80):
        if self.cached_installed_mods:
            return self.cached_installed_mods

        dayz_path = self.config.get("dayz_path")
        if not dayz_path or not os.path.exists(dayz_path):
            return "DayZ path not set or invalid. Check Settings (F4)."
        
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, color_system="standard", width=width)
        
        try:
            mods = [] 
            
            paths_to_check = [dayz_path]
            workshop_path = os.path.join(dayz_path, "!Workshop")
            if os.path.exists(workshop_path):
                paths_to_check.append(workshop_path)

            for p in paths_to_check:
                for entry in os.listdir(p):
                    if entry.startswith("@"):
                        full_path = os.path.join(p, entry)
                        name = self.get_mod_name(full_path)
                        mods.append((name, entry))
            
            try:
                base_steam = os.path.dirname(os.path.dirname(dayz_path))
                sid_path = os.path.join(base_steam, "workshop", "content", "221100")
                if os.path.exists(sid_path):
                    for sid in os.listdir(sid_path):
                        s_mod_path = os.path.join(sid_path, sid)
                        if os.path.isdir(s_mod_path):
                            name = self.get_mod_name(s_mod_path)
                            mods.append((name, sid))
            except:
                pass

            if not mods:
                try:
                    output.close()
                except Exception:
                    pass
                try:
                    console.close()
                except Exception:
                    pass
                return f"No mods found.\nChecked:\n- {dayz_path}\n- {workshop_path}\n\n:("
            
            unique_names = sorted(list(set(m[0] for m in mods)), key=lambda x: x.lower())
            
            total = len(unique_names)
            cols = 3
            rows = 24
            per_page = cols * rows
            
            total_pages = (total + per_page - 1) // per_page
            if total_pages < 1: total_pages = 1
            
            if self.mods_page >= total_pages: self.mods_page = total_pages - 1
            if self.mods_page < 0: self.mods_page = 0
            
            start = self.mods_page * per_page
            end = min(start + per_page, total)
            page_mods = unique_names[start:end]
            
            header = f"[bold yellow]PAGE {self.mods_page + 1}/{total_pages}[/bold yellow] (Total: {total})"
            
            table = Table(box=None, padding=(0, 1), expand=True, show_header=True, header_style="bold white", title=header, title_justify="left")
            for _ in range(cols):
                table.add_column("Mod Name", style="cyan", no_wrap=True, overflow="ellipsis", header_style="dim")
            
            table.show_header = False 

            for i in range(0, len(page_mods), cols):
                row = page_mods[i:i+cols]
                while len(row) < cols: row.append("")
                table.add_row(*row)

            try:
                output.close()
            except Exception:
                pass
            try:
                console.close()
            except Exception:
                pass
            output = io.StringIO()
            if width < 80: width = 80
            console = Console(file=output, force_terminal=True, width=width)
            console.print(table)
            result = ANSI(output.getvalue())
            self.cached_installed_mods = result
            try:
                output.close()
            except Exception:
                pass
            try:
                console.close()
            except Exception:
                pass
            return result
        except Exception as e:
            return f"Error reading mods: {e}"
