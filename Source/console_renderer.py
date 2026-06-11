import io
from rich.console import Console
from prompt_toolkit.formatted_text import ANSI

from constants import PING_GREEN, PING_YELLOW


def ping_color(ping_val):
    if not isinstance(ping_val, int):
        return "white"
    if ping_val <= PING_GREEN:
        return "green"
    if ping_val <= PING_YELLOW:
        return "yellow"
    return "red"


def render_to_ansi(render_func, width, color_system="standard"):
    output = io.StringIO()
    console = Console(
        file=output,
        force_terminal=True,
        color_system=color_system,
        width=width
    )
    try:
        render_func(console)
    finally:
        try:
            console.close()
        except Exception:
            pass
    result = ANSI(output.getvalue())
    try:
        output.close()
    except Exception:
        pass
    return result


def render_table_to_ansi(table, width):
    return render_to_ansi(lambda c: c.print(table), width)
