"""Main application window."""
from __future__ import annotations

import threading
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from app.gui.dashboard import DashboardPage
from app.gui.profiles import ProfilesPage
from app.gui.wifi_page import WifiPage, WifiPasswordDialog
from app.backend import wireguard, wifi

DEFAULT_WIDTH = 900
DEFAULT_HEIGHT = 600
MIN_WIDTH = 640
MIN_HEIGHT = 420
APP_TITLE = "Wi-Fi & VPN"

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title=APP_TITLE)
        self.set_default_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.set_size_request(MIN_WIDTH, MIN_HEIGHT)

        # State
        self._op_state = "idle"  # idle, loading_profiles, connecting, disconnecting
        self._selected_profile = None
        self._kernel_state = "disconnected"
        self._kernel_interface = None
        self._wifi_scanning = False

        # UI
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        
        self._dashboard = DashboardPage()
        self._profiles = ProfilesPage()
        self._wifi_page = WifiPage()
        
        self._stack.add_titled(self._dashboard, "dashboard", "Dashboard")
        self._stack.add_titled(self._profiles, "profiles", "VPN Profiles")
        self._stack.add_titled(self._wifi_page, "wifi", "Wi-Fi")

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self._stack)
        switcher.set_halign(Gtk.Align.CENTER)

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title(APP_TITLE)
        header.pack_start(switcher)
        self.set_titlebar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.pack_start(self._stack, True, True, 0)
        self.add(root)

        # Wiring
        self._profiles.on_load_requested(self._on_load_profiles)
        self._profiles.on_selection_changed(self._on_profile_selected)
        self._dashboard.on_connect_clicked(self._on_connect_clicked)
        self._dashboard.on_disconnect_clicked(self._on_disconnect_clicked)
        self._wifi_page.on_scan_requested(self._on_wifi_scan)
        self._wifi_page.on_connect_requested(self._on_wifi_connect)
        self._wifi_page.on_disconnect_requested(self._on_wifi_disconnect)

        # Intercept the window close event so we hide instead of quitting
        self.connect("delete-event", self._on_delete_event)

        self.show_all()
        self._refresh_sensitivities()

        # Start polling
        GLib.timeout_add_seconds(3, self._poll_status)
        self._poll_status()

        # Auto-scan on first load (delay by 500ms to let the UI render first)
        GLib.timeout_add(500, self._initial_scan)

    def _initial_scan(self) -> bool:
        self._on_load_profiles()
        self._on_wifi_scan()
        return False  # Run only once

    def _on_delete_event(self, widget, event) -> bool:
        # Hide the window and tell GTK to ignore the close event
        self.hide()
        return True

    def _refresh_sensitivities(self) -> None:
        idle = self._op_state == "idle"
        sel = self._selected_profile is not None
        kernel = self._kernel_state
        iface_ok = self._kernel_interface == self._selected_profile

        self._profiles.set_load_enabled(idle)
        self._wifi_page.set_scan_enabled(idle and not self._wifi_scanning)
        
        self._dashboard.set_connect_sensitive(idle and sel and kernel == "disconnected")
        self._dashboard.set_disconnect_sensitive(idle and kernel == "connected" and iface_ok)

    def _poll_status(self) -> bool:
        # VPN Status
        status = wireguard.get_status()
        self._kernel_state = status["state"]
        self._kernel_interface = status["interface"]

        if self._op_state == "idle":
            self._dashboard.set_status(self._kernel_state, status.get("detail", ""))
            if self._kernel_interface:
                self._selected_profile = self._kernel_interface
                self._dashboard.set_profile(self._kernel_interface)
                self._profiles.select_profile(self._kernel_interface)
            else:
                self._dashboard.set_profile(self._selected_profile)

        # Wi-Fi Status
        wifi_status = wifi.get_current_wifi()
        if wifi_status["connected"]:
            self._wifi_page.show_status(f"Connected to: {wifi_status['ssid']}")
            self._wifi_page.set_disconnect_enabled(True)
            self._wifi_page.select_network(wifi_status["ssid"])
        else:
            self._wifi_page.show_status("Not connected to Wi-Fi")
            self._wifi_page.set_disconnect_enabled(False)

        self._refresh_sensitivities()
        return True

    def _on_profile_selected(self, name: str | None) -> None:
        self._selected_profile = name
        if self._op_state == "idle":
            self._dashboard.set_profile(name)
            self._refresh_sensitivities()

    # --- Load Profiles ---
    def _on_load_profiles(self) -> None:
        if self._op_state != "idle":
            return
        self._op_state = "loading_profiles"
        self._profiles.show_error(None)
        self._refresh_sensitivities()

        def worker():
            try:
                result = wireguard.list_profiles_privileged()
            except Exception as e:
                result = {"ok": False, "error": "worker_crashed", "detail": str(e)}
            GLib.idle_add(self._on_profiles_loaded, result)

        threading.Thread(target=worker, daemon=True).start()

    def _on_profiles_loaded(self, result: dict) -> bool:
        self._op_state = "idle"
        if result.get("ok"):
            profiles = result.get("profiles", [])
            self._profiles.set_profiles(profiles)
            if not profiles:
                self._profiles.show_error("No profiles found in /etc/wireguard.")
            else:
                self._profiles.show_error(None)
        else:
            err = result.get("detail", "Unknown error")
            self._profiles.show_error(f"Error: {err}")
        self._refresh_sensitivities()
        return False

    # --- Connect / Disconnect VPN ---
    def _start_operation(self, action: str, label: str) -> None:
        if self._op_state != "idle" or not self._selected_profile:
            return
        
        self._op_state = "connecting" if action == "up" else "disconnecting"
        state_key = "connecting" if action == "up" else "disconnecting"
        
        self._dashboard.set_status(state_key, f"{label} {self._selected_profile}...")
        self._refresh_sensitivities()

        def worker():
            if action == "up":
                result = wireguard.connect(self._selected_profile)
                expected = "connected"
            else:
                result = wireguard.disconnect(self._selected_profile)
                expected = "disconnected"

            if result["success"]:
                final = wireguard.wait_for_state(expected, self._selected_profile, timeout=4.0)
                result["final_status"] = final
            
            GLib.idle_add(self._on_op_finished, result)

        threading.Thread(target=worker, daemon=True).start()

    def _on_connect_clicked(self) -> None:
        self._start_operation("up", "Connecting to")

    def _on_disconnect_clicked(self) -> None:
        self._start_operation("down", "Disconnecting")

    def _on_op_finished(self, result: dict) -> bool:
        self._op_state = "idle"
        if not result["success"]:
            self._dashboard.set_status("error", result["message"])
        else:
            final = result.get("final_status", {"state": "unknown", "interface": None, "detail": ""})
            self._kernel_state = final["state"]
            self._kernel_interface = final.get("interface")
            self._dashboard.set_status(self._kernel_state, final.get("detail", ""))
            if self._kernel_interface:
                self._dashboard.set_profile(self._kernel_interface)
        self._refresh_sensitivities()
        return False

    # --- Wi-Fi ---
    def _on_wifi_scan(self) -> None:
        if self._wifi_scanning:
            return
        self._wifi_scanning = True
        self._wifi_page.set_scan_enabled(False)
        self._wifi_page.show_status("Scanning for networks...")

        def worker():
            networks = wifi.scan_networks()
            GLib.idle_add(self._on_wifi_scan_finished, networks)

        threading.Thread(target=worker, daemon=True).start()

    def _on_wifi_scan_finished(self, networks: list) -> bool:
        self._wifi_scanning = False
        self._wifi_page.set_networks(networks)
        self._refresh_sensitivities()
        return False

    def _on_wifi_connect(self, ssid: str) -> None:
        # Check if this is a saved network
        saved_networks = wifi.get_saved_connections()
        password = None

        if ssid not in saved_networks:
            # Prompt for password only if not saved
            dialog = WifiPasswordDialog(self, ssid)
            response = dialog.run()
            password = dialog.get_password()
            dialog.destroy()

            if response != Gtk.ResponseType.OK:
                return

        self._wifi_page.show_status(f"Connecting to {ssid}...")
        
        def worker():
            result = wifi.connect_wifi(ssid, password)
            GLib.idle_add(self._on_wifi_connect_finished, ssid, result)

        threading.Thread(target=worker, daemon=True).start()

    def _on_wifi_connect_finished(self, ssid: str, result: dict) -> bool:
        if result["success"]:
            self._wifi_page.show_status(f"Connected to: {ssid}")
        else:
            self._wifi_page.show_status(f"Failed: {result['message']}")
        self._poll_status()
        return False

    def _on_wifi_disconnect(self) -> None:
        self._wifi_page.show_status("Disconnecting...")
        self._wifi_page.set_disconnect_enabled(False)
        
        def worker():
            result = wifi.disconnect_wifi()
            GLib.idle_add(self._on_wifi_disconnect_finished, result)

        threading.Thread(target=worker, daemon=True).start()

    def _on_wifi_disconnect_finished(self, result: dict) -> bool:
        if result["success"]:
            self._wifi_page.show_status("Disconnected")
        else:
            self._wifi_page.show_status(f"Failed: {result['message']}")
        self._poll_status()
        return False
