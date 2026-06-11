from prompt_toolkit.layout import Layout, HSplit, Window, FormattedTextControl, FloatContainer, DynamicContainer
from prompt_toolkit.layout.dimension import Dimension
from constants import APP_NAME, VERSION
from launch_dialog import LaunchDialog


class UILayout:
    def __init__(self, tui, view_renderer, tabs):
        self.tui = tui
        self.view_renderer = view_renderer
        self.tabs = tabs
        self.launch_dialog = LaunchDialog(tui)

    def init_widgets(self):
        for tab in self.tabs.values():
            tab.init_widgets()

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
                Window(content=FormattedTextControl(text=lambda: self.view_renderer.get_tabs_text(tui.current_tab, tui.tabs)), height=1, always_hide_cursor=True),
                DynamicContainer(get_body),
                Window(content=FormattedTextControl(text=lambda: self.view_renderer.get_footer_text(tui.latest_update_info)), height=1, always_hide_cursor=True),
            ]),
            floats=[
                self.launch_dialog.get_container()
            ]
        )

        return tui.root_container
