"""Gtk.Application entry point for the Proton VPN WireGuard Manager.

Kept deliberately thin: it owns the application lifecycle only.
The window and all widgets live in app/gui/main_window.py so that
later assignments (dashboard, profiles) can add pages without
touching startup code.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from app.gui.main_window import MainWindow
from app.gui.tray import TrayIcon  # noqa: E402

APP_ID = "io.github.gproton.wifivpn"


class WifiVpnApplication(Gtk.Application):
    """Application object. One window, built on first activate."""

    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        self._window: MainWindow | None = None

    def quit_app(self) -> None:
        if self._window:
            self._window.destroy()
        self.quit()

    def do_activate(self) -> None:
        if self._window is None:
            self._window = MainWindow(application=self)
            self._tray = TrayIcon(self._window, self)
            
        # Check if we should start minimized
        import os
        if os.environ.get("WIFI_VPN_MINIMIZED") == "1":
            self._window.hide()
        else:
            self._window.show_all()
            self._window.present()
