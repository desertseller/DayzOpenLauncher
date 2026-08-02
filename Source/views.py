from html import escape as html_escape
import platform
from rich.table import Table
from rich import box
from prompt_toolkit.filters import has_focus
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout import HSplit, VSplit, Window, FormattedTextControl
from prompt_toolkit.widgets import Frame, Label
from prompt_toolkit.key_binding import KeyBindings
from constants import BUILD_INFO
from console_renderer import render_table_to_ansi, ping_color


class ViewRenderer:
    def __init__(self, config, app_instance=None):
        self.config = config
        self.app = app_instance

    TAB_LABELS = {
        "GLOBAL": "Global",
        "FAVRECENT": "Recent/Favorites",
        "SETTINGS": "Settings",
        "MODS": "Mods",
    }

    def get_tabs_text(self, current_tab, tabs):
        parts = []
        for tab in tabs:
            key = f"F{tabs.index(tab) + 1}"
            label = self.TAB_LABELS.get(tab, tab)
            if tab == current_tab:
                parts.append(f"<ansiyellow><b> [{key}: {label}] </b></ansiyellow>")
            else:
                parts.append(f"  {key}: {label}  ")
        return HTML("".join(parts))

    def get_footer_text(self, update_info=None):
        tabs_count = len(self.app.tabs) if self.app else 4
        footer = (
            f" <b>F1-F{tabs_count}</b>: Tabs | "
            f"<b>F7</b>: Fav | <b>F8</b>: Refresh | <b>Ctrl+D</b>: Direct Connect | <b>Ctrl+C</b>: Quit | "
            f"<b>PageUp/PageDown</b>: Scroll Page | <b>Build:</b> {BUILD_INFO} "
        )
        if update_info:
            footer += f" <ansiyellow>Update available: {update_info['tag']}</ansiyellow> "
        return HTML(footer)

    def get_settings_view(self, nick_input, dayz_path_input, toggle_control, battleye_toggle_control):
        rows = [
            self._focus_label("Survivor Name", nick_input),
            Window(height=1),
            Frame(nick_input),
            Window(height=1),
            self._focus_label("Installation Path", dayz_path_input),
            Window(height=1),
            Frame(dayz_path_input),
            Window(height=1),
            self._focus_label("Launch & Close", toggle_control),
            Window(height=1),
            VSplit([
                toggle_control,
                Window(),
            ]),
        ]

        if platform.system() == "Windows":
            rows += [
                Window(height=1),
                self._focus_label("Disable BattlEye", battleye_toggle_control),
                Window(height=1),
                VSplit([
                    battleye_toggle_control,
                    Window(),
                ]),
            ]

        return Frame(
            HSplit([
                Window(height=1),
                VSplit([
                    Window(width=4),
                    HSplit(rows),
                    Window(width=4),
                ]),
                Window(),
            ], padding=0),
            title="Settings"
        )

    @staticmethod
    def _focus_label(text, control):
        def get_text():
            prefix = "&gt; " if has_focus(control)() else "  "
            return HTML(f"<ansiyellow><b>{prefix}{html_escape(text)}</b></ansiyellow>")
        return Label(text=get_text)

    def _render_server_table(self, filtered_servers, selected_index, live_info, width, rows, is_active_pane=True):
        table = Table(box=box.MINIMAL, expand=True, show_header=True, header_style="bold cyan")
        table.add_column("SERVER NAME", no_wrap=True)
        table.add_column("PLAYERS", width=10, justify="right")
        table.add_column("QUEUE", width=8, justify="right")
        table.add_column("MAP", width=12)
        table.add_column("TIME", width=8)
        table.add_column("PING", width=8, justify="right")

        height = max(rows - 10, 20)
        start = max(0, selected_index - (height // 2))
        end = min(len(filtered_servers), start + height)

        fav_keys = self._build_fav_keys()

        for i in range(start, end):
            server = filtered_servers[i]
            is_sel = (i == selected_index)
            is_fav = (str(server.get('ip')), str(server.get('port'))) in fav_keys
            style = self._row_style(is_sel, is_fav, is_active_pane)

            live = live_info.get((server.get('ip'), server.get('port')))
            ping_display = self._format_ping(
                live.get('ping') if live else server.get('ping', '?'),
                is_sel and is_active_pane
            )

            queue_val = live.get('queue', 0) if live else server.get('queue', 0)
            q_display = str(int(queue_val)) if str(queue_val).isdigit() else "0"

            name_display = server.get('name', 'Unknown')
            if is_fav:
                name_display = f"* {name_display}"

            table.add_row(
                name_display[:(width - 50)],
                f"{live.get('players', '?') if live else server.get('players', '?')}/"
                f"{live.get('max_players', '?') if live else server.get('max_players', '?')}",
                q_display,
                str(live.get('map') or server.get('map', 'Unknown')) if live else str(server.get('map', 'Unknown')),
                str(live.get('time', server.get('time', '00:00'))) if live else str(server.get('time', '00:00')),
                ping_display,
                style=style
            )

        return self._render_console_table(table, width)

    def _build_fav_keys(self):
        favs = self.config.get("servers", [])
        return {(str(f.get('ip')), str(f.get('port'))) for f in favs}

    @staticmethod
    def _row_style(is_selected, is_favorite, is_active_pane):
        sel = is_selected and is_active_pane
        if is_favorite:
            return "bold yellow on blue" if sel else "bold yellow"
        return "bold white on blue" if sel else ""

    @staticmethod
    def _format_ping(ping_val, is_selected=False):
        if ping_val == '?' or ping_val is None:
            return "?"
        try:
            p = int(ping_val)
        except (ValueError, TypeError):
            return str(ping_val)

        color = ping_color(p)
        if is_selected:
            return f"[bold {color}]{ping_val}[/bold {color}]"
        return f"[{color}]{ping_val}[/{color}]"

    @staticmethod
    def _render_console_table(table, width):
        return render_table_to_ansi(table, width)

    def get_server_list_text(self, filtered_servers, selected_index, live_info, loading, current_tab, output_size, search_text=""):
        if loading and current_tab == "GLOBAL":
            return HTML("<ansigreen>Fetching servers data...</ansigreen>")

        if current_tab == "GLOBAL" and not search_text and not filtered_servers:
            return HTML("<ansiyellow>Type server name...</ansiyellow>")

        if not filtered_servers and not loading:
            if current_tab == "GLOBAL" and search_text:
                return HTML(f"<ansired>No servers found matching: '{html_escape(search_text)}'</ansired>")
            return HTML("<ansiyellow>Type server name...</ansiyellow>") if current_tab == "GLOBAL" else "No servers found."

        cols, rows = output_size
        width = max(cols - 46, 80)
        return self._render_server_table(filtered_servers, selected_index, live_info, width, rows)

    def get_pane_server_list_text(self, filtered_servers, selected_index, live_info, output_size, is_active_pane=False):
        if not filtered_servers:
            return "No servers found."
        cols, rows = output_size
        width = max(cols, 80)
        return self._render_server_table(filtered_servers, selected_index, live_info, width, rows, is_active_pane)
