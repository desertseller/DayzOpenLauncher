import io
from rich.console import Console
from prompt_toolkit.formatted_text import ANSI

from constants import PING_GREEN, PING_YELLOW

_global_console = Console(force_terminal=True, color_system="standard", width=80)


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
    
    _global_console.file = output
    _global_console.width = width
    
    try:
        render_func(_global_console)
    finally:
        pass
        
    result = ANSI(output.getvalue())
    try:
        output.close()
    except Exception:
        pass
    return result


def render_table_to_ansi(table, width):
    return render_to_ansi(lambda c: c.print(table), width)
