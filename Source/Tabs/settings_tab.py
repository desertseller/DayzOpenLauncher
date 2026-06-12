from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout import Window, FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from constants import DEFAULT_PROFILE_NAME
from console_renderer import render_to_ansi


class SettingsTab:
    def __init__(self, tui):
        self.tui = tui
        self.settings_content = None

    def _get_toggle_text(self):
        def render(console):
            on = self.tui.data_manager.config.get("launch_and_close", False)
            if on:
                console.print(
                    f"[bold white on green]  ON  [/bold white on green]"
                    f" [dim] Enter to toggle[/dim]"
                )
            else:
                console.print(
                    f"[bold white on red]  OFF [/bold white on red]"
                    f" [dim] Enter to toggle[/dim]"
                )
        return render_to_ansi(render, 28)

    def init_widgets(self):
        tui = self.tui

        tui.nick_input = TextArea(
            height=1, multiline=False,
            text=str(tui.data_manager.config.get("profile_name", DEFAULT_PROFILE_NAME) or "")
        )
        tui.nick_input.buffer.on_text_changed += lambda _: tui.data_manager.config.set("profile_name", tui.nick_input.text, save=False)

        tui.dayz_path_input = TextArea(
            height=1, multiline=False,
            text=str(tui.data_manager.config.get("dayz_path", "") or "")
        )
        tui.dayz_path_input.buffer.on_text_changed += lambda _: tui.data_manager.config.set("dayz_path", tui.dayz_path_input.text, save=False)

        tui.launch_close_control = FormattedTextControl(
            text=lambda: self._get_toggle_text(),
            focusable=True,
        )

        toggle_kb = KeyBindings()
        @toggle_kb.add('enter')
        def _toggle(event):
            current = tui.data_manager.config.get("launch_and_close", False)
            tui.data_manager.config.set("launch_and_close", not current)
            event.app.invalidate()
        tui.launch_close_control.key_bindings = toggle_kb

        tui.launch_close_window = Window(
            content=tui.launch_close_control,
            width=28,
            always_hide_cursor=True,
            height=1,
        )

    def init_layout(self):
        tui = self.tui
        self.settings_content = tui.view_renderer.get_settings_view(
            tui.nick_input,
            tui.dayz_path_input,
            tui.launch_close_window
        )

    def get_body(self):
        return self.settings_content

    def get_focus_control(self):
        return self.tui.nick_input
