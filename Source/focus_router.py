class FocusRouter:
    def __init__(self, tui):
        self.tui = tui

    def focus_default_control(self):
        tui = self.tui
        focus_map = {
            "SETTINGS": tui.nick_input,
            "MODS": tui.installed_mods_control,
        }
        target = focus_map.get(tui.current_tab)
        if tui.current_tab == "FAVRECENT":
            target = (tui.recent_control if tui.favrecent_pane == "recent"
                      else tui.favorites_control)
        if target is None:
            target = tui.content_control
        try:
            tui.app.layout.focus(target)
        except Exception:
            pass

    def focus_tab_control(self, tab_name):
        tui = self.tui
        focus_map = {
            "SETTINGS": tui.tab_settings.get_focus_control(),
            "MODS": tui.tab_mods.get_focus_control(),
        }
        target = focus_map.get(tab_name)
        if tab_name == "FAVRECENT":
            target = tui.tab_favrecent.get_focus_control()
        if target is None:
            target = tui.tab_global.get_focus_control()

        try:
            tui.app.layout.focus(target)
            if hasattr(target, 'buffer') and hasattr(target.buffer, 'cursor_position'):
                target.buffer.cursor_position = len(target.text)
        except (ValueError, AttributeError):
            try:
                tui.app.layout.focus(tui.search_filter)
            except Exception:
                pass

    def safe_focus(self, control):
        try:
            self.tui.app.layout.focus(control)
            if hasattr(control, 'buffer') and hasattr(control.buffer, 'cursor_position'):
                control.buffer.cursor_position = len(control.text)
        except Exception:
            pass


def scroll_list(servers, current_index, direction, rows):
    page_size = max(1, rows - 10)
    delta = direction * page_size
    return max(0, min(len(servers) - 1, current_index + delta))
