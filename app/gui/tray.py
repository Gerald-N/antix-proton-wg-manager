"""System Tray Applet using Gtk.StatusIcon."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import threading

from app.backend import wireguard, wifi

class TrayIcon:
    def __init__(self, window, app):
        self._window = window
        self._app = app
        self._updating = False

        self._icon = Gtk.StatusIcon()
        self._icon.set_from_icon_name("network-wireless")
        self._icon.set_tooltip_text("Wi-Fi & VPN")
        self._icon.connect("popup-menu", self._on_popup_menu)
        self._icon.connect("activate", self._on_activate)

        self._menu = Gtk.Menu()
        
        # Status headers
        self._item_wifi_status = Gtk.MenuItem(label="Wi-Fi: Checking...")
        self._item_wifi_status.set_sensitive(False)
        self._menu.append(self._item_wifi_status)

        self._item_vpn_status = Gtk.MenuItem(label="VPN: Checking...")
        self._item_vpn_status.set_sensitive(False)
        self._menu.append(self._item_vpn_status)

        self._menu.append(Gtk.SeparatorMenuItem())

        # Wi-Fi Submenu
        self._wifi_menu_item = Gtk.MenuItem(label="Connect Wi-Fi")
        self._wifi_submenu = Gtk.Menu()
        self._wifi_menu_item.set_submenu(self._wifi_submenu)
        self._menu.append(self._wifi_menu_item)

        # VPN Submenu
        self._vpn_menu_item = Gtk.MenuItem(label="Connect VPN")
        self._vpn_submenu = Gtk.Menu()
        self._vpn_menu_item.set_submenu(self._vpn_submenu)
        self._menu.append(self._vpn_menu_item)

        self._menu.append(Gtk.SeparatorMenuItem())

        self._item_disconnect_wifi = Gtk.MenuItem(label="Disconnect Wi-Fi")
        self._item_disconnect_wifi.connect("activate", self._on_disconnect_wifi)
        self._menu.append(self._item_disconnect_wifi)

        self._item_disconnect_vpn = Gtk.MenuItem(label="Disconnect VPN")
        self._item_disconnect_vpn.connect("activate", self._on_disconnect_vpn)
        self._menu.append(self._item_disconnect_vpn)

        self._menu.append(Gtk.SeparatorMenuItem())

        self._item_show = Gtk.MenuItem(label="Show Window")
        self._item_show.connect("activate", self._on_show_window)
        self._menu.append(self._item_show)

        self._item_quit = Gtk.MenuItem(label="Quit")
        self._item_quit.connect("activate", self._on_quit)
        self._menu.append(self._item_quit)

        self._menu.show_all()

        GLib.timeout_add_seconds(3, self._update_status)

    def _on_activate(self, icon):
        self._on_show_window(None)

    def _on_show_window(self, widget):
        self._window.show_all()
        self._window.present()

    def _on_popup_menu(self, icon, button, time):
        self._menu.popup(None, None, None, icon, button, time)

    def _on_quit(self, widget):
        self._app.quit_app()

    def _on_disconnect_wifi(self, widget):
        def worker():
            wifi.disconnect_wifi()
            GLib.idle_add(self._update_status)
        threading.Thread(target=worker, daemon=True).start()

    def _on_disconnect_vpn(self, widget):
        status = wireguard.get_status()
        iface = status.get("interface")
        if not iface:
            return
        def worker():
            wireguard.disconnect(iface)
            GLib.idle_add(self._update_status)
        threading.Thread(target=worker, daemon=True).start()

    def _on_connect_wifi(self, widget, ssid):
        def worker():
            wifi.connect_wifi(ssid)
            GLib.idle_add(self._update_status)
        threading.Thread(target=worker, daemon=True).start()

    def _on_connect_vpn(self, widget, profile):
        def worker():
            wireguard.connect(profile)
            GLib.idle_add(self._update_status)
        threading.Thread(target=worker, daemon=True).start()

    def _update_status(self) -> bool:
        if self._updating:
            return True
        self._updating = True

        def worker():
            vpn = wireguard.get_status()
            wifi_status = wifi.get_current_wifi()
            
            # Fetch available lists for submenus
            saved_wifi = wifi.get_saved_connections()
            vpn_profiles = wireguard.list_profiles_privileged().get("profiles", [])

            GLib.idle_add(self._apply_status, vpn, wifi_status, saved_wifi, vpn_profiles)

        threading.Thread(target=worker, daemon=True).start()
        return True

    def _apply_status(self, vpn, wifi_status, saved_wifi, vpn_profiles) -> bool:
        # Update Status Labels
        vpn_text = f"VPN: Connected ({vpn['interface']})" if vpn["state"] == "connected" else "VPN: Disconnected"
        wifi_text = f"Wi-Fi: {wifi_status['ssid']}" if wifi_status["connected"] else "Wi-Fi: Disconnected"
        
        self._item_vpn_status.set_label(vpn_text)
        self._item_wifi_status.set_label(wifi_text)
        
        self._item_disconnect_wifi.set_sensitive(wifi_status["connected"])
        self._item_disconnect_vpn.set_sensitive(vpn["state"] == "connected")

        # Update Icon
        if not wifi_status["connected"]:
            icon_name = "nm-signal-00"
            tooltip = "Disconnected"
        else:
            sig = wifi_status.get("signal", 100)
            if sig > 75: lvl = "100"
            elif sig > 50: lvl = "75"
            elif sig > 25: lvl = "50"
            else: lvl = "25"
            
            if vpn["state"] == "connected":
                icon_name = f"nm-signal-{lvl}-secure"
                tooltip = f"VPN Active ({vpn['interface']})"
            else:
                icon_name = f"nm-signal-{lvl}"
                tooltip = f"Wi-Fi Connected ({wifi_status['ssid']})"
            
        self._icon.set_from_icon_name(icon_name)
        self._icon.set_tooltip_text(tooltip)

        # Rebuild Wi-Fi submenu
        for child in self._wifi_submenu.get_children():
            self._wifi_submenu.remove(child)
        for ssid in saved_wifi:
            item = Gtk.MenuItem(label=ssid)
            item.connect("activate", self._on_connect_wifi, ssid)
            self._wifi_submenu.append(item)
            
        # Rebuild VPN submenu
        for child in self._vpn_submenu.get_children():
            self._vpn_submenu.remove(child)
        for prof in vpn_profiles:
            item = Gtk.MenuItem(label=prof)
            item.connect("activate", self._on_connect_vpn, prof)
            self._vpn_submenu.append(item)

        self._menu.show_all()
        self._updating = False
        return False
