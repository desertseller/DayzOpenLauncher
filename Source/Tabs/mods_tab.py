from prompt_toolkit.layout import Window, FormattedTextControl
from prompt_toolkit.widgets import Frame
from prompt_toolkit.key_binding import KeyBindings


class ModsTab:
    def __init__(self, tui):
        self.tui = tui
        self.mods_content = None

    def init_widgets(self):
        tui = self.tui

        mods_kb = KeyBindings()

        @mods_kb.add('right')
        def _mods_page_next(event):
            tui.mod_manager.mods_page += 1
            event.app.invalidate()

        @mods_kb.add('left')
        def _mods_page_prev(event):
            if tui.mod_manager.mods_page > 0:
                tui.mod_manager.mods_page -= 1
            event.app.invalidate()

        tui.installed_mods_control = FormattedTextControl(
            text=lambda: tui.mod_manager.get_installed_mods_text(
                width=tui.app.renderer.output.get_size().columns if hasattr(tui, 'app') else 80
            ),
            focusable=True,
            key_bindings=mods_kb
        )

    def init_layout(self):
        tui = self.tui
        self.mods_content = Frame(
            Window(content=tui.installed_mods_control),
            title="Mods"
        )

    def get_body(self):
        return self.mods_content

    def get_focus_control(self):
        return self.tui.installed_mods_control
