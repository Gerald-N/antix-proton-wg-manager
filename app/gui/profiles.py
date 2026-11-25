"""Profiles page: ListBox, Load button, error banner.

Public API:
    set_profiles(names)          replace the list
    get_selected() -> str|None
    on_selection_changed(cb)     cb(name|None)
    on_load_requested(cb)        cb()
    set_load_enabled(bool)
    show_error(str|None)
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

ROW_NAME_ATTR = "_profile_name"

class ProfilesPage(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_border_width(24)

        # Header row: Load button + Error banner
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self._load_btn = Gtk.Button(label="Load Profiles")
        self._load_btn.connect("clicked", lambda _b: self._on_load_clicked())
        header_box.pack_start(self._load_btn, False, False, 0)

        self._error_label = Gtk.Label()
        self._error_label.set_halign(Gtk.Align.START)
        self._error_label.set_line_wrap(True)
        self._error_label.get_style_context().add_class("error")
        self._error_label.hide()
        header_box.pack_start(self._error_label, True, True, 0)

        self.pack_start(header_box, False, False, 0)

        # ---- List -----------------------------------------------------
        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.set_activate_on_single_click(True)
        self._listbox.connect("row-selected", self._on_row_selected)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_hexpand(True)
        scroller.add(self._listbox)
        scroller.set_shadow_type(Gtk.ShadowType.IN)
        self.pack_start(scroller, True, True, 0)

        self._empty_label = Gtk.Label(label="No profiles loaded.")
        self._empty_label.get_style_context().add_class("dim-label")
        self._empty_label.set_margin_top(24)
        self._listbox.set_placeholder(self._empty_label)

        # ---- Callbacks -------------------------------------------------
        self._on_selection_cb = None
        self._on_load_cb = None

    # ---- Public API ---------------------------------------------------
    def set_profiles(self, names: list[str]) -> None:
        for child in list(self._listbox.get_children()):
            self._listbox.remove(child)
        for name in names:
            self._append_row(name)

    def select_profile(self, name: str) -> bool:
        for row in self._listbox.get_children():
            if getattr(row, ROW_NAME_ATTR, None) == name:
                self._listbox.select_row(row)
                return True
        return False

    def get_selected(self) -> str | None:
        row = self._listbox.get_selected_row()
        return getattr(row, ROW_NAME_ATTR, None) if row else None

    def on_selection_changed(self, cb) -> None:
        self._on_selection_cb = cb

    def on_load_requested(self, cb) -> None:
        self._on_load_cb = cb

    def set_load_enabled(self, enabled: bool) -> None:
        self._load_btn.set_sensitive(enabled)
        if enabled:
            self._load_btn.set_label("Load Profiles")
        else:
            self._load_btn.set_label("Loading...")

    def show_error(self, msg: str | None) -> None:
        if msg:
            self._error_label.set_text(msg)
            self._error_label.show()
        else:
            self._error_label.hide()

    # ---- Internal -----------------------------------------------------
    def _append_row(self, name: str) -> None:
        row = Gtk.ListBoxRow()
        setattr(row, ROW_NAME_ATTR, name)
        label = Gtk.Label(label=name)
        label.set_xalign(0.0)
        label.set_margin_top(6)
        label.set_margin_bottom(6)
        label.set_margin_start(8)
        label.set_margin_end(8)
        row.add(label)
        self._listbox.add(row)
        row.show_all()

    def _on_row_selected(self, _lb, row) -> None:
        if self._on_selection_cb is not None:
            name = getattr(row, ROW_NAME_ATTR, None) if row is not None else None
            self._on_selection_cb(name)

    def _on_load_clicked(self) -> None:
        if self._on_load_cb is not None:
            self._on_load_cb()
