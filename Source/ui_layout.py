from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, FloatContainer, Float, DynamicContainer, ConditionalContainer
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import Frame, Label, Button, Shadow
from prompt_toolkit.filters import Condition
from constants import APP_NAME, VERSION


class UILayout:
    def __init__(self, tui, view_renderer, tabs):
        self.tui = tui
        self.view_renderer = view_renderer
        self.tabs = tabs

    def init_widgets(self):
        tui = self.tui

        for tab in self.tabs.values():
            tab.init_widgets()

        tui.launch_ok_btn = Button("OK", handler=tui._close_launch)

    def init_layout(self):
        tui = self.tui

        for tab in self.tabs.values():
            tab.init_layout()

        tab_global = self.tabs["GLOBAL"]

        def get_body():
            if tui.current_tab == "SETTINGS":
                return self.tabs["SETTINGS"].get_body()
            elif tui.current_tab == "MODS":
                return self.tabs["MODS"].get_body()
            elif tui.current_tab == "FAVRECENT":
                return self.tabs["FAVRECENT"].get_body()
            return tab_global.get_body()

        tui.root_container = FloatContainer(
            content=HSplit([
                tab_global.search_frame,
                tab_global.title_frame,
                Window(content=FormattedTextControl(text=lambda: self.view_renderer.get_tabs_text(tui.current_tab, tui.tabs)), height=1),
                DynamicContainer(get_body),
                Window(content=FormattedTextControl(text=lambda: self.view_renderer.get_footer_text(tui.latest_update_info)), height=1),
            ]),
            floats=[
                Float(content=ConditionalContainer(
                    content=self.get_launch_dialog(),
                    filter=Condition(lambda: tui.show_launch_dialog)
                ))
            ]
        )

        return tui.root_container

    def get_launch_dialog(self):
        return Shadow(
            body=Frame(
                HSplit([
                    Label(text=lambda: self.tui.launch_message),
                ], padding=1),
                title="Launching Game",
                width=50,
            )
        )
