from prompt_toolkit.widgets import TextArea
from constants import DEFAULT_PROFILE_NAME


class SettingsTab:
    def __init__(self, tui):
        self.tui = tui
        self.settings_content = None

    def init_widgets(self):
        tui = self.tui

        tui.nick_input = TextArea(
            height=1, multiline=False,
            text=str(tui.data_manager.config.get("profile_name", DEFAULT_PROFILE_NAME) or "")
        )
        tui.nick_input.buffer.on_text_changed += lambda _: tui.data_manager.config.set("profile_name", tui.nick_input.text)

        tui.dayz_path_input = TextArea(
            height=1, multiline=False,
            text=str(tui.data_manager.config.get("dayz_path", "") or "")
        )
        tui.dayz_path_input.buffer.on_text_changed += lambda _: tui.data_manager.config.set("dayz_path", tui.dayz_path_input.text)

    def init_layout(self):
        tui = self.tui
        self.settings_content = tui.view_renderer.get_settings_view(
            tui.nick_input,
            tui.dayz_path_input
        )

    def get_body(self):
        return self.settings_content

    def get_focus_control(self):
        return self.tui.nick_input
