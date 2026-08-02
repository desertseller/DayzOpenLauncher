import os
import sys
import platform
import threading
import time
import traceback

if getattr(sys, 'frozen', False):
    root_dir = os.path.dirname(sys.executable)
    internal_dir = os.path.join(root_dir, "_internal")
    if os.path.exists(internal_dir):
        sys.path.insert(0, internal_dir)
else:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, root_dir)

try:
    from prompt_toolkit import Application
    from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, FloatContainer, Float, DynamicContainer, ConditionalContainer
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.widgets import Frame, TextArea, Label, Button, Shadow, RadioList
    from prompt_toolkit.widgets.base import Border
    from prompt_toolkit.patch_stdout import patch_stdout

    Border.TOP_LEFT = "\u256d"
    Border.TOP_RIGHT = "\u256e"
    Border.BOTTOM_LEFT = "\u2570"
    Border.BOTTOM_RIGHT = "\u256f"
except ImportError as e:
    print(f"Error: Missing libraries or import error: {e}")
    traceback.print_exc()
    sys.exit(1)

from data_manager import DataManager
from live_updates import LiveUpdater
from mod_manager import ModManager
from server_actions import ServerActions
from views import ViewRenderer
from keybindings import KeyBinder
from constants import VERSION, APP_NAME, DEFAULT_PROFILE_NAME
from ui_layout import UILayout
from focus_router import FocusRouter
from Tabs import GlobalTab, FavrecentTab, SettingsTab, ModsTab

if platform.system() == "Windows":
    try:
        from windows.utils import setup_env, get_steam_path, get_dayz_path, is_dayz_running
        from windows.launcher import launch_dayz
        setup_env()
    except Exception:
        def get_steam_path():
            return None
        def get_dayz_path(p):
            return None
        def is_dayz_running():
            return False
        def launch_dayz(*args):
            return False
else:
    sys.stdout.write("\x1b]2;DayzOpenLauncher\x07")
    try:
        from linux.utils import setup_env, get_steam_path, get_dayz_path, is_dayz_running
        from linux.launcher import launch_dayz
        setup_env()
    except ImportError:
        def get_steam_path():
            return None
        def get_dayz_path(p):
            return None
        def is_dayz_running():
            return False
        def launch_dayz(*args):
            return False


class DayZLauncherTUI:

    def __init__(self):
        self.running = True
        self._init_data()
        self._init_state()
        self.focus_router = FocusRouter(self)
        self._init_ui()
        self._init_background_loops()

    def _init_data(self):
        self.data_manager = DataManager()
        self.mod_manager = ModManager(self.data_manager.config)
        self.server_actions = ServerActions(self.data_manager.config)
        self.view_renderer = ViewRenderer(self.data_manager.config, self)
        self._ensure_dayz_path()

        self.tab_global = GlobalTab(self)
        self.tab_favrecent = FavrecentTab(self)
        self.tab_settings = SettingsTab(self)
        self.tab_mods = ModsTab(self)

        self.tab_map = {
            "GLOBAL": self.tab_global,
            "FAVRECENT": self.tab_favrecent,
            "SETTINGS": self.tab_settings,
            "MODS": self.tab_mods,
        }

    def _ensure_dayz_path(self):
        current_path = self.data_manager.config.get("dayz_path")

        path_invalid = False
        if current_path and current_path != "CANNOT FIND PATH":
            if platform.system() == "Windows":
                if current_path.startswith("/"):
                    path_invalid = True
            else:
                if "\\" in current_path or ":" in current_path:
                    path_invalid = True

        if not current_path or path_invalid or current_path == "CANNOT FIND PATH":
            steam = get_steam_path()
            path = get_dayz_path(steam)
            if path:
                self.data_manager.config.set("dayz_path", path)
            elif not current_path:
                self.data_manager.config.set("dayz_path", "CANNOT FIND PATH")

    def _init_state(self):
        self.refresh_lock = threading.Lock()
        self.search_timer = None
        self.current_tab = "GLOBAL"
        self.tabs = ["GLOBAL", "FAVRECENT", "SETTINGS", "MODS"]
        self.show_launch_dialog = False
        self.launch_message = ""
        self.show_direct_connect = False
        self.latest_update_info = None
        self.run_update_on_exit = False

    # TAB STATE ===============================[

    @property
    def selected_index(self):
        return self.tab_global.selected_index

    @selected_index.setter
    def selected_index(self, value):
        self.tab_global.selected_index = value

    @property
    def recent_selected_index(self):
        return self.tab_favrecent.recent_selected_index

    @recent_selected_index.setter
    def recent_selected_index(self, value):
        self.tab_favrecent.recent_selected_index = value

    @property
    def favorites_selected_index(self):
        return self.tab_favrecent.favorites_selected_index

    @favorites_selected_index.setter
    def favorites_selected_index(self, value):
        self.tab_favrecent.favorites_selected_index = value

    @property
    def favrecent_pane(self):
        return self.tab_favrecent.favrecent_pane

    @favrecent_pane.setter
    def favrecent_pane(self, value):
        self.tab_favrecent.favrecent_pane = value

    @property
    def active_pane_servers(self):
        return (self.data_manager.favrecent_recent if self.favrecent_pane == "recent"
                else self.data_manager.favrecent_favorites)

    @property
    def active_pane_index(self):
        return (self.recent_selected_index if self.favrecent_pane == "recent"
                else self.favorites_selected_index)

    def set_active_pane_index(self, value):
        if self.favrecent_pane == "recent":
            self.recent_selected_index = value
        else:
            self.favorites_selected_index = value


    def _init_ui(self):
        self.live_updater = LiveUpdater(
            self.data_manager.browser,
            self.data_manager.live_info,
            lambda: self.app.invalidate() if hasattr(self, 'app') else None,
            self.data_manager.live_info_lock
        )

        self.ui_layout = UILayout(self, self.view_renderer, self.tab_map)
        self.ui_layout.init_widgets()

        self.key_binder = KeyBinder(self)
        self.kb = self.key_binder.get_global_bindings()

        self.content_control.key_bindings = self.tab_global.get_list_keybindings()

        favrecent_kb = self.tab_favrecent.get_list_keybindings()
        self.recent_control.key_bindings = favrecent_kb
        self.favorites_control.key_bindings = favrecent_kb

        self.root_container = self.ui_layout.init_layout()

        self.app = Application(
            layout=Layout(self.root_container, focused_element=self.content_control),
            key_bindings=self.kb,
            mouse_support=True,
            full_screen=True,
        )

    def _init_background_loops(self):
        def _get_live_servers():
            if self.current_tab == "FAVRECENT":
                return self.data_manager.favrecent_recent + self.data_manager.favrecent_favorites
            return self.data_manager.filtered_servers

        def _get_live_index():
            if self.current_tab == "FAVRECENT":
                return 0
            return self.selected_index

        self.live_updater.start_loop(_get_live_servers, _get_live_index)

        self.refresh_data()
        self._start_mod_loop()

        from update_checker import UpdateChecker
        self.update_checker = UpdateChecker(self)
        self.update_checker.start_check()

    def _start_mod_loop(self):
        def _mod_checker():
            while self.running:
                try:
                    time.sleep(10)
                    if not self.running:
                        break
                    if self.current_tab == "MODS" and not self.mod_manager.cached_installed_mods:
                        if hasattr(self, 'app'):
                            self.app.invalidate()
                except Exception:
                    pass

        threading.Thread(target=_mod_checker, daemon=True).start()


    def _open_direct_connect(self):
        self.show_direct_connect = True
        self.ui_layout.direct_connect_dialog.clear()
        self.app.invalidate()
        try:
            control = self.ui_layout.direct_connect_dialog.textarea.control
            if control:
                self.app.layout.focus(control)
        except Exception:
            pass

    def _close_direct_connect(self):
        self.show_direct_connect = False
        self.app.invalidate()
        try:
            self.app.layout.focus(self.content_control)
        except Exception:
            pass

    def _handle_direct_connect(self, text):
        text = text.strip()
        if not text:
            return

        if ':' in text:
            ip, port_str = text.rsplit(':', 1)
            ip = ip.strip()
            port_str = port_str.strip()
        else:
            parts = text.split()
            if len(parts) >= 2:
                ip, port_str = parts[0].strip(), parts[1].strip()
            else:
                self.launch_message = "Error: Invalid format\nIP:PORT expected"
                self.show_launch_dialog = True
                self.show_direct_connect = False
                self.app.invalidate()
                return

        try:
            port = int(port_str)
        except (ValueError, TypeError):
            self.launch_message = "Error: Invalid port\nMust be a number"
            self.show_launch_dialog = True
            self.show_direct_connect = False
            self.app.invalidate()
            return

        dayz_path = self.data_manager.config.get("dayz_path")
        if not dayz_path or dayz_path == "CANNOT FIND PATH":
            self.launch_message = "Error: DayZ path not set\nConfigure in Settings (F3)"
            self.show_launch_dialog = True
            self.show_direct_connect = False
            self.app.invalidate()
            return

        profile_name = self.data_manager.config.get("profile_name", DEFAULT_PROFILE_NAME)

        self.show_direct_connect = False
        self.launch_message = f"Starting DayZ...\nIP: {ip}:{port}"
        self.show_launch_dialog = True
        self.app.invalidate()

        from server_actions import launch_dayz
        disable_battleye = self.data_manager.config.get("disable_battleye", False)
        if launch_dayz(dayz_path, ip, port, profile_name, disable_battleye=disable_battleye):
            if self.data_manager.config.get("launch_and_close", False):
                try:
                    self.data_manager.config.save()
                except Exception:
                    pass
                self.app.exit()
            else:
                def _hide():
                    time.sleep(2)
                    self.show_launch_dialog = False
                    self.app.invalidate()

                threading.Thread(target=_hide, daemon=True).start()
        else:
            self.launch_message = "Error: Failed to launch DayZ"
            self.app.invalidate()

    def _close_launch(self):
        self.server_actions.cancel_launch()
        self._do_close_launch()

    def _do_close_launch(self):
        self.show_launch_dialog = False
        try:
            self.app.layout.focus(self.content_control)
        except Exception:
            pass

    def refresh_data(self):
        def _worker():
            if not self.refresh_lock.acquire(blocking=False):
                return
            try:
                self.data_manager.loading = True
                if hasattr(self, 'app'):
                    self.app.invalidate()
                self.data_manager.fetch_data(force=True)
                self.update_filtered()
            finally:
                self.data_manager.loading = False
                if hasattr(self, 'app'):
                    self.app.invalidate()
                self.refresh_lock.release()

            if hasattr(self, 'update_checker'):
                self.update_checker.start_check()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_filter_change(self, buffer=None):
        self.selected_index = 0
        self.recent_selected_index = 0
        self.favorites_selected_index = 0
        self.update_filtered()

        if self.current_tab != "GLOBAL":
            return

        if self.search_timer:
            self.search_timer.cancel()

        def do_search():
            st = self.search_filter.text
            if len(st) >= 2 or (len(st) == 0 and self.data_manager.last_search_text):
                self.data_manager.fetch_data(st)
                self.update_filtered()
                if hasattr(self, 'app'):
                    self.app.invalidate()

        self.search_timer = threading.Timer(0.6, do_search)
        self.search_timer.start()

    def update_filtered(self):
        self.data_manager.update_filtered(self.current_tab, self.search_filter.text)
        if self.current_tab == "FAVRECENT":
            self._clamp_index(self.recent_selected_index, len(self.data_manager.favrecent_recent), 'recent')
            self._clamp_index(self.favorites_selected_index, len(self.data_manager.favrecent_favorites), 'favorites')
        else:
            if self.selected_index >= len(self.data_manager.filtered_servers):
                self.selected_index = max(0, len(self.data_manager.filtered_servers) - 1)

    def _clamp_index(self, current_value, list_len, attr_name):
        if current_value >= list_len:
            setattr(self, f"{attr_name}_selected_index", max(0, list_len - 1))

    def switch_tab(self, tab_name):
        if self.current_tab == "SETTINGS":
            self.data_manager.config.save()

        self.current_tab = tab_name
        self.search_filter.text = ""
        self.selected_index = 0
        self.recent_selected_index = 0
        self.favorites_selected_index = 0
        self.update_filtered()

        if hasattr(self, 'app'):
            self.app.invalidate()

        if tab_name == "MODS":
            self.mod_manager.clear_cache()

        self._focus_tab_control(tab_name)

    def _focus_tab_control(self, tab_name):
        self.focus_router.focus_tab_control(tab_name)


    def _start_dayz_monitor(self, server):
        def monitor():
            for _ in range(60):
                time.sleep(2)
                if self._is_dayz_running():
                    ip = str(server.get('ip', ''))
                    port = str(server.get('port', ''))
                    key = f"{ip}:{port}"
                    timestamps = self.data_manager.config.get("last_played_timestamps", {})
                    timestamps[key] = time.time()
                    self.data_manager.config.set("last_played_timestamps", timestamps)
                    if self.data_manager.config.get("launch_and_close", False):
                        try:
                            self.data_manager.config.save()
                        except Exception:
                            pass
                        try:
                            self.app.exit()
                        except Exception:
                            os._exit(0)
                    break

        threading.Thread(target=monitor, daemon=True).start()

    @staticmethod
    def _is_dayz_running():
        return is_dayz_running()

    def join_server_wrapper(self, server):
        def on_start(msg):
            self.launch_message = msg
            self.show_launch_dialog = True
            self.app.invalidate()

        def on_end(success, err):
            if not success:
                self.launch_message = err
            else:
                self.show_launch_dialog = False
                self._start_dayz_monitor(server)
                try:
                    self.app.layout.focus(self.content_control)
                except Exception:
                    pass
            self.app.invalidate()

        self.server_actions.join_server(server, on_start, on_end)

    # ── App lifecycle ────────────────────────────────────────────

    def run(self):
        try:
            with patch_stdout():
                try:
                    self.app.run()
                except (KeyboardInterrupt, EOFError):
                    pass
        except Exception:
            with open("crash_log.txt", "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        finally:
            self._cleanup()

    def _cleanup(self):
        self.running = False
        try:
            self.data_manager.config.save()
        except Exception:
            pass
        try:
            if hasattr(self, 'search_timer') and self.search_timer:
                self.search_timer.cancel()
        except Exception:
            pass
        try:
            if hasattr(self, 'live_updater'):
                self.live_updater.stop()
            if hasattr(self, 'data_manager') and hasattr(self.data_manager, 'browser'):
                self.data_manager.browser.close()
        except Exception:
            pass
        try:
            sys.stdout.write(
                "\033[?1000l\033[?1002l\033[?1003l\033[?1004l"
                "\033[?1005l\033[?1006l\033[?1015l\033[?25h"
            )
            sys.stdout.flush()
        except Exception:
            pass

        if not self.run_update_on_exit:
            os._exit(0)


if __name__ == "__main__":
    tui = DayZLauncherTUI()
    tui.run()
