import textwrap
import platform
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, FloatContainer, Float, DynamicContainer, ConditionalContainer
from prompt_toolkit.widgets import Frame, TextArea, Label, Button, Shadow
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition
from constants import APP_NAME, VERSION, DEFAULT_PROFILE_NAME

class UILayout:
    def __init__(self, tui, view_renderer):
        self.tui = tui
        self.view_renderer = view_renderer

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

        tui.launch_ok_btn = Button("OK", handler=tui._close_launch)

        tui.content_control = FormattedTextControl(
            text=tui.get_server_list_text,
            focusable=True
        )
        tui.content_window = Window(content=tui.content_control, cursorline=False)

        tui.recent_control = FormattedTextControl(
            text=tui.get_recent_list_text,
            focusable=True
        )
        tui.recent_window = Window(content=tui.recent_control, cursorline=False)

        tui.favorites_control = FormattedTextControl(
            text=tui.get_favorites_list_text,
            focusable=True
        )
        tui.favorites_window = Window(content=tui.favorites_control, cursorline=False)

        tui.mod_control = FormattedTextControl(text=tui.get_mod_list_text)

    def init_layout(self):
        tui = self.tui
        
        main_content = VSplit([
            Frame(tui.content_window, title="Server List"),
            Frame(Window(content=tui.mod_control), title="Server Details", width=40),
        ])

        favrecent_content = VSplit([
            Frame(tui.recent_window, title="Recent"),
            Frame(tui.favorites_window, title="Favorites"),
        ])

        mods_content = Frame(
            Window(content=tui.installed_mods_control),
            title="Mods"
        )

        settings_content = self.view_renderer.get_settings_view(
            tui.nick_input,
            tui.dayz_path_input
        )

        tui.updates_control = FormattedTextControl(
            text=lambda: self._get_updates_text(),
            focusable=True
        )
        updates_content = Frame(
            HSplit([
                Window(height=1),
                Window(content=tui.updates_control),
                Window(height=1),
            ]),
            title="Updates"
        )

        def get_body():
            if tui.current_tab == "SETTINGS":
                return settings_content
            elif tui.current_tab == "MODS":
                return mods_content
            elif tui.current_tab == "UPDATES":
                return updates_content
            elif tui.current_tab == "FAVRECENT":
                return favrecent_content
            return main_content

        tui.root_container = FloatContainer(
            content=HSplit([
                Frame(
                    tui.search_filter,
                    title=f"{APP_NAME}"
                ),
                Window(content=FormattedTextControl(text=lambda: self.view_renderer.get_tabs_text(tui.current_tab, tui.tabs)), height=1),
                DynamicContainer(get_body), 
                Window(content=FormattedTextControl(text=lambda: self.view_renderer.get_footer_text()), height=1),
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

    def _get_updates_text(self):
        if not self.tui.latest_update_info:

            return [
                ("ansiyellow bold", " --- GitHub Updates ---\n\n"),
                ("", f" Current version: {VERSION}\n\n"),
                ("ansigreen", " You are up to date!\n\n"),
                ("", " Press F8 to manually check for updates.\n"),
            ]
        
        info = self.tui.latest_update_info
        res = [
            ("ansiyellow bold", "--- New version available ---\n\n"),
            ("ansicyan", f" Version: {info['tag']}\n"),
            ("", f" Your version: {VERSION}\n\n"),
            ("ansiwhite bold", " Changelog:\n"),
        ]
        
        body = info.get("body", "")
        if body:
            raw_lines = body.splitlines()
            display_lines = []
            
            for line in raw_lines:
                if not line.strip():
                    display_lines.append("")
                    continue
                wrapped = textwrap.wrap(line, width=95, initial_indent="  ", subsequent_indent="  ")
                display_lines.extend(wrapped)
            
            for line in display_lines[:18]:
                res.append(("", f"{line}\n"))
                
            if len(display_lines) > 18:
                res.append(("", "  ...\n"))
        
        res.append(("", "\n"))
        
        update_text = " Press ENTER to open browser and download setup\n"
            
        res.append(("ansigreen bold", update_text))
        return res
