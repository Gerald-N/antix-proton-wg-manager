"""Dashboard page (Assignment 04).

Placeholder-data dashboard. No backend calls, no wg, no pkexec.

Public API consumed by later assignments:

    set_status(state, detail="")   state in {"disconnected","connecting","connected","error"}
    set_profile(name_or_none)      name=None means "(none selected)"
    set_busy(busy)                 disables both buttons while True
    on_connect_clicked(cb)
    on_disconnect_clicked(cb)

Design notes:
  * Status dot is an ASCII "●" in a Gtk.Label. Colour is hinted via
    Gtk.StyleContext classes (success/warning/error) that Adwaita
    already defines, so no custom CSS and no icon-theme dependency.
  * Buttons start insensitive: Connect because no profile is selected,
    Disconnect because we are not connected. Assignment 05 will enable
    Connect on profile select; Assignment 10 will attach the real
    callbacks and drive set_busy().
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

# StyleContext class per state -> dot colour hint
_DOT_CLASS = {
    "disconnected": "dim-label",
    "connecting":   "warning",
    "disconnecting":"warning",
    "connected":    "success",
    "error":        "error",
}

_DOT_TEXT = "●"


class DashboardPage(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.set_border_width(32)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)

        # ---- Status row ------------------------------------------------
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_box.set_halign(Gtk.Align.START)

        self._dot = Gtk.Label(label=_DOT_TEXT)
        self._dot.get_style_context().add_class(_DOT_CLASS["disconnected"])
        status_box.pack_start(self._dot, False, False, 0)

        self._status_label = Gtk.Label(label="Disconnected")
        self._status_label.set_xalign(0.0)
        status_box.pack_start(self._status_label, False, False, 0)

        status_caption = Gtk.Label(label="Status")
        status_caption.set_xalign(0.0)
        status_caption.get_style_context().add_class("dim-label")

        self.pack_start(status_caption, False, False, 0)
        self.pack_start(status_box, False, False, 0)

        # ---- Profile row -----------------------------------------------
        profile_caption = Gtk.Label(label="Server profile")
        profile_caption.set_xalign(0.0)
        profile_caption.get_style_context().add_class("dim-label")

        self._profile_label = Gtk.Label(label="(none selected)")
        self._profile_label.set_xalign(0.0)
        self._profile_label.get_style_context().add_class("dim-label")

        self.pack_start(profile_caption, False, False, 0)
        self.pack_start(self._profile_label, False, False, 0)

        # ---- Buttons ---------------------------------------------------
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.START)
        button_box.set_margin_top(12)

        self._connect_btn = Gtk.Button(label="Connect")
        self._connect_btn.get_style_context().add_class("suggested-action")
        self._connect_btn.set_sensitive(False)

        self._disconnect_btn = Gtk.Button(label="Disconnect")
        self._disconnect_btn.get_style_context().add_class("destructive-action")
        self._disconnect_btn.set_sensitive(False)

        button_box.pack_start(self._connect_btn, False, False, 0)
        button_box.pack_start(self._disconnect_btn, False, False, 0)
        self.pack_start(button_box, False, False, 0)

        # Push content to the top so the dashboard reads as a panel.
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        self.pack_start(spacer, True, True, 0)

        self._state = "disconnected"
        self._busy = False
        self._connected_profile: str | None = None

    # ---- Public API ---------------------------------------------------
    def set_status(self, state: str, detail: str = "") -> None:
        if state not in _DOT_CLASS:
            state = "disconnected"
        ctx = self._dot.get_style_context()
        for cls in set(_DOT_CLASS.values()):
            ctx.remove_class(cls)
        ctx.add_class(_DOT_CLASS[state])

        text = state.capitalize()
        if detail:
            text = f"{text} — {detail}"
        self._status_label.set_text(text)
        self._state = state
        self._refresh_buttons()

    def set_profile(self, name: str | None) -> None:
        if name:
            self._profile_label.set_text(name)
            self._profile_label.get_style_context().remove_class("dim-label")
        else:
            self._profile_label.set_text("(none selected)")
            self._profile_label.get_style_context().add_class("dim-label")
        self._refresh_buttons()

    def set_busy(self, busy: bool) -> None:
        self._busy = bool(busy)
        self._refresh_buttons()

    def on_connect_clicked(self, callback) -> None:
        self._connect_btn.connect("clicked", lambda _b: callback())

    def on_disconnect_clicked(self, callback) -> None:
        self._disconnect_btn.connect("clicked", lambda _b: callback())

    def set_connect_sensitive(self, sensitive: bool) -> None:
        self._connect_btn.set_sensitive(sensitive)

    def set_disconnect_sensitive(self, sensitive: bool) -> None:
        self._disconnect_btn.set_sensitive(sensitive)

    # ---- Internal -----------------------------------------------------
    def _refresh_buttons(self) -> None:
        if self._busy:
            self._connect_btn.set_sensitive(False)
            self._disconnect_btn.set_sensitive(False)
            return
        profile_selected = self._profile_label.get_text() != "(none selected)"
        self._connect_btn.set_sensitive(profile_selected and self._state == "disconnected")
        self._disconnect_btn.set_sensitive(self._state == "connected")
