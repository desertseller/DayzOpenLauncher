import io
from rich.table import Table
from rich.console import Console
from rich import box
from prompt_toolkit.formatted_text import ANSI, HTML
from prompt_toolkit.layout import HSplit, VSplit, Window
from prompt_toolkit.widgets import Frame,  Label
from prompt_toolkit.layout.controls import FormattedTextControl
from constants import VERSION, BUILD_INFO

class ViewRenderer:
    def __init__(self, config, app_instance=None):
        self.config = config
        self.app = app_instance

    TAB_LABELS = {
        "GLOBAL": "Global",
        "FAVRECENT": "Recent/Favorites",
        "SETTINGS": "Settings",
        "MODS": "Mods",
        "UPDATES": "Updates",
    }

    def get_tabs_text(self, current_tab, tabs):
        parts = []
        for tab in tabs:
            key = f"F{tabs.index(tab)+1}"
            label = self.TAB_LABELS.get(tab, tab)
            if tab == current_tab:
                parts.append(f"<ansiyellow><b> [{key}: {label}] </b></ansiyellow>")
            else:
                parts.append(f"  {key}: {label}  ")
        return HTML("".join(parts))

    def get_footer_text(self):
        tabs_count = len(self.app.tabs) if self.app else 4
        footer = f" <b>F1-F{tabs_count}</b>: Tabs | <b>←/→</b>: Switch between windows | <b>F7</b>: Fav | <b>F8</b>: Refresh | <b>Ctrl+C</b>: Quit | <b>PageUp/PageDown</b>: Scroll Page | <b>Build:</b> {BUILD_INFO} "
        return HTML(footer)

    def get_settings_view(self, nick_input, dayz_path_input):
        return Frame(
            HSplit([
                Window(height=1),
                VSplit([
                    Window(width=4),
                    HSplit([
                        Label(text="SURVIVOR NAME", style="ansiyellow bold"),
                        nick_input,
                        Window(height=1),
                        
                        Label(text="INSTALLATION PATH", style="ansiyellow bold"),
                        dayz_path_input,
                        
                        Window(height=2),
                    ])
                ]),
                Window(), 
            ], padding=0),
            title="Settings"
        )

    def _render_server_table(self, filtered_servers, selected_index, live_info, width, rows):
        table = Table(box=box.MINIMAL, expand=True, show_header=True, header_style="bold cyan")
        table.add_column("SEL", width=3, justify="center")
        table.add_column("SERVER NAME", no_wrap=True)
        table.add_column("PLAYERS", width=10, justify="right")
        table.add_column("QUEUE", width=8, justify="right")
        table.add_column("MAP", width=12)
        table.add_column("TIME", width=8)
        table.add_column("PING", width=6, justify="right")

        height = rows - 10
        if height < 5: height = 20

        start = max(0, selected_index - (height // 2))
        end = min(len(filtered_servers), start + height)

        favs = self.config.get("servers", [])
        fav_keys = set()
        for f in favs:
            fav_keys.add((str(f.get('ip')), str(f.get('port'))))

        for i in range(start, end):
            s = filtered_servers[i]
            is_sel = (i == selected_index)

            is_fav = (str(s.get('ip')), str(s.get('port'))) in fav_keys

            style = "bold white on blue" if is_sel else ""
            if is_fav and not is_sel:
                style = "bold yellow"
            elif is_fav and is_sel:
                style = "bold yellow on blue"

            live = live_info.get((s.get('ip'), s.get('port')))

            if live:
                queue_val = live.get('queue', 0)
                players = live.get('players', '?')
                max_players = live.get('max_players', '?')
                s_time = live.get('time', s.get('time', '00:00'))
                s_map = live.get('map') or s.get('map', 'Unknown')
                s_ping = live.get('ping', '?')
            else:
                queue_val = s.get('queue', 0)
                players = s.get('players', '?')
                max_players = s.get('max_players', '?')
                s_time = s.get('time', '00:00')
                s_map = s.get('map', 'Unknown')
                s_ping = '?'

            try:
                q_int = int(queue_val)
            except:
                q_int = 0

            q_display = str(q_int) if q_int > 0 else "0"
            p_str = f"{players}/{max_players}"

            name_display = s.get('name', 'Unknown')
            if is_fav:
                name_display = f"* {name_display}"

            ping_display = str(s_ping)
            if s_ping != '?':
                try:
                    p_val = int(s_ping)
                    if p_val <= 75: ping_display = f"[green]{s_ping}[/green]"
                    elif p_val <= 150: ping_display = f"[yellow]{s_ping}[/yellow]"
                    else: ping_display = f"[red]{s_ping}[/red]"

                    if is_sel:
                         if p_val <= 75: ping_display = f"[bold green]{s_ping}[/bold green]"
                         elif p_val <= 150: ping_display = f"[bold yellow]{s_ping}[/bold yellow]"
                         else: ping_display = f"[bold red]{s_ping}[/bold red]"
                except:
                    pass

            table.add_row(
                ">" if is_sel else " ",
                name_display[:(width-56)],
                p_str,
                q_display,
                str(s_map),
                str(s_time),
                ping_display,
                style=style
            )

        output = io.StringIO()
        console = Console(file=output, force_terminal=True, color_system="standard", width=width)
        console.print(table)
        return ANSI(output.getvalue())

    def get_server_list_text(self, filtered_servers, selected_index, live_info, loading, current_tab, output_size, search_text=""):
        if loading and current_tab == "GLOBAL":
            return HTML("<ansigreen>Fetching servers data...</ansigreen>")

        if current_tab == "GLOBAL" and not search_text and not filtered_servers:
            return HTML("<ansiyellow>Type server name...</ansiyellow>")

        if not filtered_servers and not loading:
            if current_tab == "GLOBAL" and search_text:
                return HTML(f"<ansired>No servers found matching: '{search_text}'</ansired>")
            elif current_tab == "GLOBAL":
                return HTML("<ansiyellow>Type server name...</ansiyellow>")
            return "No servers found."

        cols, rows = output_size
        width = cols - 46
        if width < 40: width = 80
        return self._render_server_table(filtered_servers, selected_index, live_info, width, rows)

    def get_pane_server_list_text(self, filtered_servers, selected_index, live_info, output_size):
        if not filtered_servers:
            return "No servers found."
        cols, rows = output_size
        width = cols
        if width < 40: width = 80
        return self._render_server_table(filtered_servers, selected_index, live_info, width, rows)