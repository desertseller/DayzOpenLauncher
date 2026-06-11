from prompt_toolkit.layout import Window, FormattedTextControl
from prompt_toolkit.widgets import Shadow
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout import ConditionalContainer, Float
from rich.panel import Panel
from rich.text import Text
from console_renderer import render_to_ansi


class LaunchDialog:

    def __init__(self, tui):
        self.tui = tui

    def get_container(self):
        return Float(
            content=ConditionalContainer(
                content=self._build_dialog(),
                filter=Condition(lambda: self.tui.show_launch_dialog)
            )
        )

    def _build_dialog(self):
        def draw(console):
            msg = self.tui.launch_message or ""
            title_text, border_style = self._classify(msg)

            lines = msg.split('\n') if msg else []
            content_lines = []
            for line in lines:
                prefix, color = self._line_style(line)
                content_lines.append(f"[{color}]{prefix} {line}[/{color}]")

            hint = self._hint(msg)
            content_lines.append("")
            content_lines.append(f"[dim]{hint}[/dim]")

            panel = Panel(
                "\n".join(content_lines) if content_lines else "",
                title=title_text,
                border_style=border_style,
                width=58,
                padding=(1, 2),
            )
            console.print(panel)

        content = FormattedTextControl(
            text=lambda: render_to_ansi(draw, 62),
            focusable=False,
        )

        return Shadow(body=Window(content=content, always_hide_cursor=True))

    def _classify(self, msg):
        if not msg:
            return "[bold cyan]DayZ Launcher[/bold cyan]", "cyan"
        if "Error" in msg or "ERROR" in msg or "Failed" in msg:
            return "[bold red] ERROR [/bold red]", "red"
        if "Download" in msg or "MOD DOWNLOAD" in msg:
            return "[bold yellow] DOWNLOADING [/bold yellow]", "yellow"
        if "Waiting" in msg or "Remaining" in msg:
            return "[bold yellow] WAITING FOR MODS [/bold yellow]", "yellow"
        if "Launching" in msg or "verified" in msg:
            return "[bold green] LAUNCHING [/bold green]", "green"
        if "Starting" in msg:
            return "[bold cyan] STARTING [/bold cyan]", "cyan"
        if "Cancel" in msg:
            return "[bold red] CANCELLED [/bold red]", "red"
        return "[bold cyan]DayZ Launcher[/bold cyan]", "cyan"

    def _hint(self, msg):
        if "Error" in msg or "ERROR" in msg or "Failed" in msg:
            return "Ctrl+Q / ENTER to close"
        return "Ctrl+Q to cancel"

    @staticmethod
    def _line_style(line):
        if "Error" in line or "ERROR" in line or "Failed" in line:
            return "[x]", "bold red"
        if "Downloading" in line or "MOD DOWNLOAD" in line:
            return "[v]", "bold yellow"
        if "Waiting" in line or "Remaining" in line or "Currently" in line:
            return "[~]", "yellow"
        if "Launching" in line or "verified" in line:
            return "[+]", "bold green"
        if "Starting" in line:
            return "[>]", "bold cyan"
        if "Opening" in line or "Workshop" in line:
            return "[*]", "cyan"
        if "IP:" in line:
            return "[o]", "cyan"
        if "Cancel" in line:
            return "[x]", "red"
        return "   ", "white"
