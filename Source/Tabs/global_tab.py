from prompt_toolkit.layout import VSplit, Window, FormattedTextControl, ConditionalContainer
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import Frame, TextArea
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition
from constants import APP_NAME


class GlobalTab:
    def __init__(self, tui):
        self.tui = tui
        self.main_content = None
        self.search_frame = None
        self.title_frame = None

    def init_widgets(self):
        tui = self.tui

        tui.search_filter = TextArea(height=1, prompt=" Search: ", multiline=False)
        tui.search_filter.buffer.on_text_changed += tui._on_filter_change

        search_kb = KeyBindings()

        @search_kb.add('down')
        @search_kb.add('up')
        def _focus_list_from_search(event):
            if tui.data_manager.filtered_servers:
                event.app.layout.focus(tui.content_control)

        tui.search_filter.control.key_bindings = search_kb

        tui.content_control = FormattedTextControl(
            text=self.get_server_list_text,
            focusable=True
        )
        tui.content_window = Window(content=tui.content_control, cursorline=False)

        tui.mod_control = FormattedTextControl(text=self.get_mod_list_text)

    def init_layout(self):
        tui = self.tui

        self.main_content = VSplit([
            Frame(tui.content_window, title="Server List", width=Dimension(weight=1)),
            Frame(Window(content=tui.mod_control), title="Server Details", width=40),
        ])

        self.search_frame = ConditionalContainer(
            content=Frame(tui.search_filter, title=f"{APP_NAME}"),
            filter=Condition(lambda: tui.current_tab == "GLOBAL")
        )

        self.title_frame = ConditionalContainer(
            content=Frame(Window(height=1), title=f"{APP_NAME}"),
            filter=Condition(lambda: tui.current_tab != "GLOBAL")
        )

    def get_body(self):
        return self.main_content

    def get_server_list_text(self):
        tui = self.tui
        if not hasattr(tui, 'app'):
            return ""
        size = tui.app.renderer.output.get_size()
        return tui.view_renderer.get_server_list_text(
            tui.data_manager.filtered_servers,
            tui.selected_index,
            tui.data_manager.live_info,
            tui.data_manager.loading,
            tui.current_tab,
            (size.columns, size.rows),
            tui.search_filter.text
        )

    def get_mod_list_text(self):
        tui = self.tui
        server = None
        if tui.data_manager.filtered_servers and tui.selected_index < len(tui.data_manager.filtered_servers):
            server = tui.data_manager.filtered_servers[tui.selected_index]

        live = None
        if server:
            live = tui.data_manager.live_info.get((server.get('ip'), server.get('port')))

        return tui.mod_manager.get_mod_list_text(server, live)

    def get_list_keybindings(self):
        tui = self.tui
        kb = KeyBindings()

        @kb.add('<any>')
        def _handle_typing(event):
            if tui.current_tab != "GLOBAL":
                return NotImplemented
            if len(event.data) == 1 and event.data.isprintable():
                tui.app.layout.focus(tui.search_filter)
                tui.search_filter.buffer.insert_text(event.data)
                tui.search_filter.buffer.cursor_position = len(tui.search_filter.text)
            else:
                return NotImplemented

        @kb.add('backspace')
        def _backspace(event):
            if tui.current_tab != "GLOBAL":
                return
            if tui.search_filter.text:
                tui.search_filter.buffer.delete_before_cursor()
                tui.selected_index = 0
                tui.recent_selected_index = 0
                tui.favorites_selected_index = 0
                tui.update_filtered()
            event.app.invalidate()

        @kb.add('up')
        def _up(event):
            if tui.selected_index > 0:
                tui.selected_index -= 1
            elif tui.current_tab == "GLOBAL":
                tui.app.layout.focus(tui.search_filter)
            event.app.invalidate()

        @kb.add('down')
        def _down(event):
            if tui.selected_index < len(tui.data_manager.filtered_servers) - 1:
                tui.selected_index += 1
            event.app.invalidate()

        @kb.add('pageup')
        def _page_up(event):
            self._scroll_page(-1, event)

        @kb.add('pagedown')
        def _page_down(event):
            self._scroll_page(1, event)

        @kb.add('enter', filter=Condition(lambda: not tui.show_launch_dialog))
        def _join(event):
            servers = tui.data_manager.filtered_servers
            idx = tui.selected_index
            if servers and 0 <= idx < len(servers):
                tui.join_server_wrapper(servers[idx])

        @kb.add('f7')
        def _favorite(event):
            servers = tui.data_manager.filtered_servers
            idx = tui.selected_index
            if servers and 0 <= idx < len(servers):
                tui.server_actions.toggle_favorite(servers[idx])
                tui.update_filtered()
                event.app.invalidate()

        return kb

    def _scroll_page(self, direction, event):
        tui = self.tui
        try:
            size = tui.app.renderer.output.get_size()
            page_size = max(1, size.rows - 10)
            delta = direction * page_size
            max_index = len(tui.data_manager.filtered_servers) - 1
            tui.selected_index = max(0, min(max_index, tui.selected_index + delta))
            event.app.invalidate()
        except Exception:
            pass

    def get_focus_control(self):
        return self.tui.content_control
