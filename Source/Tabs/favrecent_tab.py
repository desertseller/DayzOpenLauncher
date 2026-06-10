from prompt_toolkit.layout import VSplit, Window, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import Frame
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition


class FavrecentTab:
    def __init__(self, tui):
        self.tui = tui
        self.favrecent_content = None

    def init_widgets(self):
        tui = self.tui

        tui.recent_control = FormattedTextControl(
            text=self.get_recent_list_text,
            focusable=True
        )
        tui.recent_window = Window(content=tui.recent_control, cursorline=False, always_hide_cursor=True)

        tui.favorites_control = FormattedTextControl(
            text=self.get_favorites_list_text,
            focusable=True
        )
        tui.favorites_window = Window(content=tui.favorites_control, cursorline=False, always_hide_cursor=True)

    def init_layout(self):
        tui = self.tui

        self.favrecent_content = VSplit([
            Frame(tui.recent_window, title="Recent", width=Dimension(weight=1)),
            Frame(tui.favorites_window, title="Favorites", width=Dimension(weight=1)),
        ])

    def get_body(self):
        return self.favrecent_content

    def get_recent_list_text(self):
        tui = self.tui
        pane_width, rows = self._get_pane_size()
        return tui.view_renderer.get_pane_server_list_text(
            tui.data_manager.favrecent_recent,
            tui.recent_selected_index,
            tui.data_manager.live_info,
            (pane_width, rows),
            is_active_pane=(tui.favrecent_pane == "recent")
        )

    def get_favorites_list_text(self):
        tui = self.tui
        pane_width, rows = self._get_pane_size()
        return tui.view_renderer.get_pane_server_list_text(
            tui.data_manager.favrecent_favorites,
            tui.favorites_selected_index,
            tui.data_manager.live_info,
            (pane_width, rows),
            is_active_pane=(tui.favrecent_pane == "favorites")
        )

    def _get_pane_size(self):
        tui = self.tui
        if not hasattr(tui, 'app'):
            return (80, 24)
        size = tui.app.renderer.output.get_size()
        pane_width = max(40, size.columns // 2 - 4)
        return pane_width, size.rows

    def get_list_keybindings(self):
        tui = self.tui
        kb = KeyBindings()

        @kb.add('left', filter=Condition(lambda: tui.current_tab == "FAVRECENT"))
        def _pane_left(event):
            tui.favrecent_pane = "recent"
            tui.app.layout.focus(tui.recent_control)
            event.app.invalidate()

        @kb.add('right', filter=Condition(lambda: tui.current_tab == "FAVRECENT"))
        def _pane_right(event):
            tui.favrecent_pane = "favorites"
            tui.app.layout.focus(tui.favorites_control)
            event.app.invalidate()

        @kb.add('up')
        def _up(event):
            self._adjust_pane_index(-1)
            event.app.invalidate()

        @kb.add('down')
        def _down(event):
            self._adjust_pane_index(1)
            event.app.invalidate()

        @kb.add('pageup')
        def _page_up(event):
            self._scroll_page(-1, event)

        @kb.add('pagedown')
        def _page_down(event):
            self._scroll_page(1, event)

        @kb.add('enter', filter=Condition(lambda: not tui.show_launch_dialog))
        def _join(event):
            servers = tui.active_pane_servers
            idx = tui.active_pane_index
            if servers and 0 <= idx < len(servers):
                tui.join_server_wrapper(servers[idx])

        @kb.add('f7')
        def _favorite(event):
            servers = tui.active_pane_servers
            idx = tui.active_pane_index
            if servers and 0 <= idx < len(servers):
                tui.server_actions.toggle_favorite(servers[idx])
                tui.update_filtered()
                event.app.invalidate()

        return kb

    def _adjust_pane_index(self, delta):
        tui = self.tui
        idx = tui.active_pane_index + delta
        servers = tui.active_pane_servers
        if 0 <= idx < len(servers):
            tui.set_active_pane_index(idx)

    def _scroll_page(self, direction, event):
        tui = self.tui
        try:
            size = tui.app.renderer.output.get_size()
            page_size = max(1, size.rows - 10)
            delta = direction * page_size
            servers = tui.active_pane_servers
            idx = tui.active_pane_index
            new_idx = max(0, min(len(servers) - 1, idx + delta))
            tui.set_active_pane_index(new_idx)
            event.app.invalidate()
        except Exception:
            pass

    def get_focus_control(self):
        tui = self.tui
        return tui.recent_control if tui.favrecent_pane == "recent" else tui.favorites_control
