from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import has_focus
from focus_router import FocusRouter


class KeyBinder:
    def __init__(self, tui):
        self.tui = tui
        self.focus_router = FocusRouter(tui)

    def get_global_bindings(self):
        kb = KeyBindings()
        tui = self.tui
        router = self.focus_router

        @kb.add('/')
        def _focus_search(event):
            if tui.current_tab != "GLOBAL":
                return
            event.app.layout.focus(tui.search_filter)
            tui.search_filter.buffer.cursor_position = len(tui.search_filter.text)

        @kb.add('c-c')
        def _exit(event):
            try:
                if hasattr(tui, 'live_updater'):
                    tui.live_updater.stop()
            except Exception:
                pass
            event.app.exit()

        @kb.add('tab')
        def _tab_focus(event):
            self._handle_tab(event)

        @kb.add('c-q')
        def _close_dialog(event):
            if tui.show_launch_dialog:
                tui._close_launch()
                return
            router.focus_default_control()

        @kb.add('enter')
        def _enter_close_error(event):
            if tui.show_launch_dialog:
                msg = tui.launch_message or ""
                if "Error" in msg or "ERROR" in msg or "Failed" in msg:
                    tui._do_close_launch()

        @kb.add('f8')
        def _refresh(event):
            tui.refresh_data()

        @kb.add('f1')
        def _global(event): tui.switch_tab("GLOBAL")
        @kb.add('f2')
        def _favrecent(event): tui.switch_tab("FAVRECENT")
        @kb.add('f3')
        def _settings(event): tui.switch_tab("SETTINGS")
        @kb.add('f4')
        def _mods(event): tui.switch_tab("MODS")

        @kb.add('f7')
        def _favorite_global(event):
            if tui.current_tab in ("GLOBAL", "FAVRECENT"):
                self._toggle_current_favorite(event)

        @kb.add('down', filter=has_focus(tui.nick_input))
        def _focus_dayz_path(event):
            router.safe_focus(tui.dayz_path_input)

        @kb.add('up', filter=has_focus(tui.dayz_path_input))
        def _focus_nick(event):
            router.safe_focus(tui.nick_input)

        return kb

    def _handle_tab(self, event):
        tui = self.tui
        router = self.focus_router
        try:
            if tui.current_tab == "SETTINGS":
                self._cycle_settings_focus(event)
                return

            target = self._target_control()
            layout = event.app.layout
            if tui.current_tab == "GLOBAL" and layout.has_focus(tui.search_filter):
                layout.focus(target)
            elif layout.has_focus(target):
                if tui.current_tab == "GLOBAL":
                    layout.focus(tui.search_filter)
                    tui.search_filter.buffer.cursor_position = len(tui.search_filter.text)
                else:
                    layout.focus(target)
            else:
                layout.focus(target)
        except (ValueError, AttributeError):
            pass

    def _cycle_settings_focus(self, event):
        router = self.focus_router
        layout = event.app.layout
        if layout.has_focus(self.tui.nick_input):
            router.safe_focus(self.tui.dayz_path_input)
        else:
            router.safe_focus(self.tui.nick_input)

    def _target_control(self):
        tui = self.tui
        tab = tui.current_tab
        if tab == "MODS":
            return tui.installed_mods_control
        if tab == "FAVRECENT":
            return (tui.recent_control if tui.favrecent_pane == "recent"
                    else tui.favorites_control)
        return tui.content_control

    def _toggle_current_favorite(self, event):
        tui = self.tui
        if tui.current_tab == "FAVRECENT":
            servers = tui.active_pane_servers
            idx = tui.active_pane_index
        else:
            servers = tui.data_manager.filtered_servers
            idx = tui.selected_index

        if servers and 0 <= idx < len(servers):
            tui.server_actions.toggle_favorite(servers[idx])
            tui.update_filtered()
            event.app.invalidate()
