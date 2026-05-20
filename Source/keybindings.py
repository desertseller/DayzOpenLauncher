from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import has_focus, Condition

class KeyBinder:
    def __init__(self, tui):
        self.tui = tui
    
    def get_global_bindings(self):
        kb = KeyBindings()
        
        @kb.add('/')
        def _focus_search(event):
            event.app.layout.focus(self.tui.search_filter)
            self.tui.search_filter.buffer.cursor_position = len(self.tui.search_filter.text)

        @kb.add('c-c')
        def _exit(event):
            try:
                if hasattr(self.tui, 'live_updater'):
                    self.tui.live_updater.stop()
            except:
                pass
            event.app.exit()

        @kb.add('tab')
        def _tab_focus(event):
            try:
                if self.tui.current_tab == "SETTINGS":
                    if event.app.layout.has_focus(self.tui.nick_input):
                        event.app.layout.focus(self.tui.dayz_path_input)
                        self.tui.dayz_path_input.buffer.cursor_position = len(self.tui.dayz_path_input.text)
                    elif event.app.layout.has_focus(self.tui.dayz_path_input):
                        event.app.layout.focus(self.tui.nick_input)
                        self.tui.nick_input.buffer.cursor_position = len(self.tui.nick_input.text)
                    else:
                        event.app.layout.focus(self.tui.nick_input)
                        self.tui.nick_input.buffer.cursor_position = len(self.tui.nick_input.text)
                else:
                    target_control = self.tui.content_control
                    if self.tui.current_tab == "MODS":
                        target_control = self.tui.installed_mods_control
                    elif self.tui.current_tab == "FAVRECENT":
                        target_control = self.tui.recent_control if self.tui.favrecent_pane == "recent" else self.tui.favorites_control

                    if event.app.layout.has_focus(self.tui.search_filter):
                        event.app.layout.focus(target_control)
                    else:
                        event.app.layout.focus(self.tui.search_filter)
                        self.tui.search_filter.buffer.cursor_position = len(self.tui.search_filter.text)
            except (ValueError, AttributeError):
                pass

        @kb.add('escape')
        def _close_dialog(event):
            if self.tui.show_launch_dialog:
                 self.tui._close_launch()
                 return

            try:
                if self.tui.current_tab == "SETTINGS":
                    event.app.layout.focus(self.tui.nick_input)
                elif self.tui.current_tab == "MODS":
                    event.app.layout.focus(self.tui.installed_mods_control)
                elif self.tui.current_tab == "FAVRECENT":
                    target = self.tui.recent_control if self.tui.favrecent_pane == "recent" else self.tui.favorites_control
                    event.app.layout.focus(target)
                else:
                    event.app.layout.focus(self.tui.content_control)
            except:
                pass


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
        @kb.add('f5')
        def _updates(event): self.tui.switch_tab("UPDATES")

        @kb.add('enter', filter=Condition(lambda: self.tui.current_tab == "UPDATES" and not self.tui.show_launch_dialog))
        def _start_update(event):
            if self.tui.latest_update_info:
                if hasattr(self.tui, 'update_checker'):
                    self.tui.update_checker.start_update_process()
                else:
                    import webbrowser
                    webbrowser.open(self.tui.latest_update_info.get("url", "https://github.com/PawelKawka/DayzOpenLauncher/releases"))

        @kb.add('f7')
        def _favorite_global(event):
            if self.tui.current_tab in ["GLOBAL", "FAVRECENT"]:
                if self.tui.current_tab == "FAVRECENT":
                    servers = self.tui.active_pane_servers
                    idx = self.tui.active_pane_index
                else:
                    servers = self.tui.data_manager.filtered_servers
                    idx = self.tui.selected_index
                if servers and 0 <= idx < len(servers):
                    server = servers[idx]
                    self.tui.server_actions.toggle_favorite(server)
                    self.tui.update_filtered()
                    event.app.invalidate()

        @kb.add('down', filter=has_focus(self.tui.nick_input))
        def _focus_dayz_path(event):
            try:
                event.app.layout.focus(self.tui.dayz_path_input)
                self.tui.dayz_path_input.buffer.cursor_position = len(self.tui.dayz_path_input.text)
            except:
                pass

        @kb.add('up', filter=has_focus(self.tui.dayz_path_input))
        def _focus_nick(event):
            try:
                event.app.layout.focus(self.tui.nick_input)
                self.tui.nick_input.buffer.cursor_position = len(self.tui.nick_input.text)
            except:
                pass

        return kb

    def get_list_bindings(self):
        kb = KeyBindings()

        @kb.add('<any>')
        def _handle_typing(event):
            if len(event.data) == 1 and event.data.isprintable():
                self.tui.app.layout.focus(self.tui.search_filter)
                self.tui.search_filter.buffer.insert_text(event.data)
                self.tui.search_filter.buffer.cursor_position = len(self.tui.search_filter.text)
            else:
                return NotImplemented

        @kb.add('backspace')
        def _backspace(event):
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
                idx = self.tui.active_pane_index
                if idx > 0:
                    self.tui.set_active_pane_index(idx - 1)
                else:
                    event.app.layout.focus(self.tui.search_filter)
            else:
                if self.tui.selected_index > 0:
                    self.tui.selected_index -= 1
                elif self.tui.current_tab != "SETTINGS":
                    event.app.layout.focus(self.tui.search_filter)
            event.app.invalidate()

        @kb.add('down')
        def _down(event):
            if self.tui.current_tab == "FAVRECENT":
                servers = self.tui.active_pane_servers
                idx = self.tui.active_pane_index
                if idx < len(servers) - 1:
                    self.tui.set_active_pane_index(idx + 1)
            else:
                if self.tui.selected_index < len(self.tui.data_manager.filtered_servers) - 1:
                    self.tui.selected_index += 1
            event.app.invalidate()

        @kb.add('left', filter=Condition(lambda: self.tui.current_tab == "FAVRECENT"))
        def _pane_left(event):
            self.tui.favrecent_pane = "recent"
            event.app.layout.focus(self.tui.recent_control)
            event.app.invalidate()

        @kb.add('right', filter=Condition(lambda: self.tui.current_tab == "FAVRECENT"))
        def _pane_right(event):
            self.tui.favrecent_pane = "favorites"
            event.app.layout.focus(self.tui.favorites_control)
            event.app.invalidate()

        @kb.add('pageup')
        def _page_up(event):
            if hasattr(self.tui, 'app'):
                try:
                    size = self.tui.app.renderer.output.get_size()
                    page_size = max(1, size.rows - 10)
                    if self.tui.current_tab == "FAVRECENT":
                        idx = self.tui.active_pane_index
                        self.tui.set_active_pane_index(max(0, idx - page_size))
                    else:
                        self.tui.selected_index = max(0, self.tui.selected_index - page_size)
                    event.app.invalidate()
                except:
                    pass

        @kb.add('pagedown')
        def _page_down(event):
            if hasattr(self.tui, 'app'):
                try:
                    size = self.tui.app.renderer.output.get_size()
                    page_size = max(1, size.rows - 10)
                    if self.tui.current_tab == "FAVRECENT":
                        servers = self.tui.active_pane_servers
                        idx = self.tui.active_pane_index
                        max_index = len(servers) - 1
                        self.tui.set_active_pane_index(min(max_index, idx + page_size))
                    else:
                        max_index = len(self.tui.data_manager.filtered_servers) - 1
                        self.tui.selected_index = min(max_index, self.tui.selected_index + page_size)
                    event.app.invalidate()
                except:
                    pass

        @kb.add('enter', filter=Condition(lambda: not self.tui.show_launch_dialog))
        def _join(event):
            try:
                if self.tui.current_tab == "UPDATES":
                    return

                if self.tui.current_tab == "FAVRECENT":
                    servers = self.tui.active_pane_servers
                    idx = self.tui.active_pane_index
                else:
                    servers = self.tui.data_manager.filtered_servers
                    idx = self.tui.selected_index

                if servers and 0 <= idx < len(servers):
                    server = servers[idx]
                    self.tui.join_server_wrapper(server)
            except Exception as e:
                with open("key_error.log", "a") as f:
                    f.write(f"Join error: {e}\n")

        @kb.add('f7')
        def _favorite(event):
            if self.tui.current_tab == "FAVRECENT":
                servers = self.tui.active_pane_servers
                idx = self.tui.active_pane_index
            else:
                servers = self.tui.data_manager.filtered_servers
                idx = self.tui.selected_index
            if servers and 0 <= idx < len(servers):
                server = servers[idx]
                self.tui.server_actions.toggle_favorite(server)
                self.tui.update_filtered()
                event.app.invalidate()

        return kb
