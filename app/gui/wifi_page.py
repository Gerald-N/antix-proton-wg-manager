"""Wi-Fi page: list networks, connect, show current status."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

ROW_SSID_ATTR = "_wifi_ssid"

class WifiPage(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_border_width(24)

        # Top header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self._scan_btn = Gtk.Button(label="Scan Networks")
        self._scan_btn.connect("clicked", lambda _b: self._on_scan_clicked())
        header_box.pack_start(self._scan_btn, False, False, 0)

        self._disconnect_btn = Gtk.Button(label="Disconnect")
        self._disconnect_btn.connect("clicked", lambda _b: self._on_disconnect_clicked())
        self._disconnect_btn.set_sensitive(False)
        header_box.pack_start(self._disconnect_btn, False, False, 0)

        self._status_label = Gtk.Label(label="Checking status...")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_margin_start(12)
        header_box.pack_start(self._status_label, True, True, 0)

        self.pack_start(header_box, False, False, 0)

        # List
        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.connect("row-activated", self._on_row_activated)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_hexpand(True)
        scroller.add(self._listbox)
        scroller.set_shadow_type(Gtk.ShadowType.IN)
        self.pack_start(scroller, True, True, 0)

        self._empty_label = Gtk.Label(label="Click Scan to find Wi-Fi networks.")
        self._empty_label.get_style_context().add_class("dim-label")
        self._empty_label.set_margin_top(24)
        self._listbox.set_placeholder(self._empty_label)

        # Callbacks
        self._on_scan_cb = None
        self._on_connect_cb = None
        self._on_disconnect_cb = None

    def set_scan_enabled(self, enabled: bool) -> None:
        self._scan_btn.set_sensitive(enabled)
        self._scan_btn.set_label("Scan Networks" if enabled else "Scanning...")

    def show_status(self, text: str) -> None:
        self._status_label.set_text(text)

    def select_network(self, ssid: str) -> None:
        for row in self._listbox.get_children():
            if getattr(row, "_wifi_ssid", None) == ssid:
                self._listbox.select_row(row)
                return

    def set_networks(self, networks: list[dict]) -> None:
        for child in list(self._listbox.get_children()):
            self._listbox.remove(child)
        for net in networks:
            self._append_row(net)

    def on_scan_requested(self, cb) -> None:
        self._on_scan_cb = cb

    def on_connect_requested(self, cb) -> None:
        self._on_connect_cb = cb

    def on_disconnect_requested(self, cb) -> None:
        self._on_disconnect_cb = cb

    def set_disconnect_enabled(self, enabled: bool) -> None:
        self._disconnect_btn.set_sensitive(enabled)

    def _on_scan_clicked(self) -> None:
        if self._on_scan_cb:
            self._on_scan_cb()

    def _on_disconnect_clicked(self) -> None:
        if self._on_disconnect_cb:
            self._on_disconnect_cb()

    def _on_row_activated(self, _lb, row) -> None:
        ssid = getattr(row, ROW_SSID_ATTR, None)
        if ssid and self._on_connect_cb:
            self._on_connect_cb(ssid)

    def _append_row(self, net: dict) -> None:
        ssid = net["ssid"]
        signal = net["signal"]
        security = net["security"]
        
        row = Gtk.ListBoxRow()
        setattr(row, ROW_SSID_ATTR, ssid)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        # Simple signal icon representation
        bars = "▂▄▆█" if signal > 75 else "▂▄▆_" if signal > 50 else "▂▄__" if signal > 25 else "▂___"
        
        label_ssid = Gtk.Label(label=ssid)
        label_ssid.set_xalign(0.0)
        
        label_signal = Gtk.Label(label=bars)
        label_signal.get_style_context().add_class("dim-label")
        
        label_sec = Gtk.Label(label=security)
        label_sec.get_style_context().add_class("dim-label")
        label_sec.set_margin_start(12)

        box.pack_start(label_ssid, True, True, 0)
        box.pack_start(label_signal, False, False, 0)
        box.pack_start(label_sec, False, False, 0)

        row.add(box)
        self._listbox.add(row)
        row.show_all()

class WifiPasswordDialog(Gtk.Dialog):
    def __init__(self, parent, ssid: str):
        super().__init__(
            title=f"Connect to {ssid}",
            transient_for=parent,
            flags=0
        )
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Connect", Gtk.ResponseType.OK
        )
        self.set_default_size(300, 100)
        
        box = self.get_content_area()
        box.set_spacing(12)
        
        label = Gtk.Label(label=f"Enter password for {ssid}:")
        label.set_xalign(0.0)
        box.pack_start(label, False, False, 0)
        
        self._entry = Gtk.Entry()
        self._entry.set_visibility(False)
        self._entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self._entry.set_placeholder_text("Password")
        box.pack_start(self._entry, False, False, 0)
        
        self.show_all()

    def get_password(self) -> str:
        return self._entry.get_text()
