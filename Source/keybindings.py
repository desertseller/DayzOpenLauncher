from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import has_focus, Condition


class KeyBinder:
    def __init__(self, tui):
        self.tui = tui

#global bindings

    def get_global_bindings(self):
        kb = KeyBindings()

        @kb.add('/')
        def _focus_search(event):
            if self.tui.current_tab != "GLOBAL":
                return
            event.app.layout.focus(self.tui.search_filter)
            self.tui.search_filter.buffer.cursor_position = len(self.tui.search_filter.text)

        @kb.add('c-c')
        def _exit(event):
            try:
                if hasattr(self.tui, 'live_updater'):
                    self.tui.live_updater.stop()
            except Exception:
                pass
            event.app.exit()

        @kb.add('tab')
        def _tab_focus(event):
            self._handle_tab(event)

        @kb.add('escape')
        def _close_dialog(event):
            if self.tui.show_launch_dialog:
                self.tui._close_launch()
                return
            self._focus_default_control()

        @kb.add('f8')
        def _refresh(event):
            self.tui.refresh_data()

        @kb.add('f1')
        def _global(event): self.tui.switch_tab("GLOBAL")
        @kb.add('f2')
        def _favrecent(event): self.tui.switch_tab("FAVRECENT")
        @kb.add('f3')
        def _settings(event): self.tui.switch_tab("SETTINGS")
        @kb.add('f4')
        def _mods(event): self.tui.switch_tab("MODS")

        @kb.add('f7')
        def _favorite_global(event):
            if self.tui.current_tab in ("GLOBAL", "FAVRECENT"):
                self._toggle_current_favorite(event)

        @kb.add('down', filter=has_focus(self.tui.nick_input))
        def _focus_dayz_path(event):
            self._safe_focus(self.tui.dayz_path_input)

        @kb.add('up', filter=has_focus(self.tui.dayz_path_input))
        def _focus_nick(event):
            self._safe_focus(self.tui.nick_input)

        return kb

    def _handle_tab(self, event):
        try:
            if self.tui.current_tab == "SETTINGS":
                self._cycle_settings_focus(event)
                return

            target = self._target_control()
            layout = event.app.layout
            if self.tui.current_tab == "GLOBAL" and layout.has_focus(self.tui.search_filter):
                layout.focus(target)
            elif layout.has_focus(target):
                if self.tui.current_tab == "GLOBAL":
                    layout.focus(self.tui.search_filter)
                    self.tui.search_filter.buffer.cursor_position = len(self.tui.search_filter.text)
                else:
                    layout.focus(target)
            else:
                layout.focus(target)
        except (ValueError, AttributeError):
            pass

    def _cycle_settings_focus(self, event):
        layout = event.app.layout
        if layout.has_focus(self.tui.nick_input):
            self._safe_focus(self.tui.dayz_path_input)
        else:
            self._safe_focus(self.tui.nick_input)

    def _target_control(self):
        tab = self.tui.current_tab
        if tab == "MODS":
            return self.tui.installed_mods_control
        if tab == "FAVRECENT":
            return (self.tui.recent_control if self.tui.favrecent_pane == "recent"
                    else self.tui.favorites_control)
        return self.tui.content_control

    def _focus_default_control(self):
        focus_map = {
            "SETTINGS": self.tui.nick_input,
            "MODS": self.tui.installed_mods_control,
        }
        target = focus_map.get(self.tui.current_tab)
        if self.tui.current_tab == "FAVRECENT":
            target = (self.tui.recent_control if self.tui.favrecent_pane == "recent"
                      else self.tui.favorites_control)
        if target is None:
            target = self.tui.content_control
        try:
            self.tui.app.layout.focus(target)
        except Exception:
            pass

    def _safe_focus(self, control):
        try:
            self.tui.app.layout.focus(control)
            if hasattr(control, 'buffer') and hasattr(control.buffer, 'cursor_position'):
                control.buffer.cursor_position = len(control.text)
        except Exception:
            pass

    def _toggle_current_favorite(self, event):
        servers, idx = self._current_server_and_index()
        if servers and 0 <= idx < len(servers):
            self.tui.server_actions.toggle_favorite(servers[idx])
            self.tui.update_filtered()
            event.app.invalidate()

#list bindings

    def get_list_bindings(self):
        kb = KeyBindings()

        @kb.add('<any>')
        def _handle_typing(event):
            if self.tui.current_tab != "GLOBAL":
                return NotImplemented
            if len(event.data) == 1 and event.data.isprintable():
                self.tui.app.layout.focus(self.tui.search_filter)
                self.tui.search_filter.buffer.insert_text(event.data)
                self.tui.search_filter.buffer.cursor_position = len(self.tui.search_filter.text)
            else:
                return NotImplemented

        @kb.add('backspace')
        def _backspace(event):
            if self.tui.current_tab != "GLOBAL":
                return
            if self.tui.search_filter.text:
                self.tui.search_filter.buffer.delete_before_cursor()
                self.tui.selected_index = 0
                self.tui.recent_selected_index = 0
                self.tui.favorites_selected_index = 0
                self.tui.update_filtered()
            event.app.invalidate()

        @kb.add('up')
        def _up(event):
            if self.tui.current_tab == "FAVRECENT":
                self._adjust_pane_index(-1)
            else:
                if self.tui.selected_index > 0:
                    self.tui.selected_index -= 1
                elif self.tui.current_tab == "GLOBAL":
                    self.tui.app.layout.focus(self.tui.search_filter)
            event.app.invalidate()

        @kb.add('down')
        def _down(event):
            if self.tui.current_tab == "FAVRECENT":
                self._adjust_pane_index(1)
            else:
                if self.tui.selected_index < len(self.tui.data_manager.filtered_servers) - 1:
                    self.tui.selected_index += 1
            event.app.invalidate()

        @kb.add('left', filter=Condition(lambda: self.tui.current_tab == "FAVRECENT"))
        def _pane_left(event):
            self.tui.favrecent_pane = "recent"
            self.tui.app.layout.focus(self.tui.recent_control)
            event.app.invalidate()

        @kb.add('right', filter=Condition(lambda: self.tui.current_tab == "FAVRECENT"))
        def _pane_right(event):
            self.tui.favrecent_pane = "favorites"
            self.tui.app.layout.focus(self.tui.favorites_control)
            event.app.invalidate()

        @kb.add('pageup')
        def _page_up(event):
            self._scroll_page(-1, event)

        @kb.add('pagedown')
        def _page_down(event):
            self._scroll_page(1, event)

        @kb.add('enter', filter=Condition(lambda: not self.tui.show_launch_dialog))
        def _join(event):
            try:
                servers, idx = self._current_server_and_index()
                if servers and 0 <= idx < len(servers):
                    self.tui.join_server_wrapper(servers[idx])
            except Exception as e:
                with open("key_error.log", "a", encoding="utf-8") as f:
                    f.write(f"Join error: {e}\n")

        @kb.add('f7')
        def _favorite(event):
            servers, idx = self._current_server_and_index()
            if servers and 0 <= idx < len(servers):
                self.tui.server_actions.toggle_favorite(servers[idx])
                self.tui.update_filtered()
                event.app.invalidate()

        return kb

    def _current_server_and_index(self):
        if self.tui.current_tab == "FAVRECENT":
            return self.tui.active_pane_servers, self.tui.active_pane_index
        return self.tui.data_manager.filtered_servers, self.tui.selected_index

    def _adjust_pane_index(self, delta):
        idx = self.tui.active_pane_index + delta
        servers = self.tui.active_pane_servers
        if 0 <= idx < len(servers):
            self.tui.set_active_pane_index(idx)

    def _scroll_page(self, direction, event):
        if not hasattr(self.tui, 'app'):
            return
        try:
            size = self.tui.app.renderer.output.get_size()
            page_size = max(1, size.rows - 10)
            delta = direction * page_size

            if self.tui.current_tab == "FAVRECENT":
                servers = self.tui.active_pane_servers
                idx = self.tui.active_pane_index
                new_idx = max(0, min(len(servers) - 1, idx + delta))
                self.tui.set_active_pane_index(new_idx)
            else:
                max_index = len(self.tui.data_manager.filtered_servers) - 1
                self.tui.selected_index = max(0, min(max_index, self.tui.selected_index + delta))
            event.app.invalidate()
        except Exception:
            pass
