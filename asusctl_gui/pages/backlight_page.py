"""
backlight_page.py
─────────────────
Screenpad brightness controls via asusctl backlight.
"""

import threading
from gi.repository import Adw, Gtk, GLib
from ..backend import asusctl


class BacklightPage(Gtk.Box):

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)
        self._suppress = False
        self._build()

    def _build(self):
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header.add_css_class("page-header")
        title = Gtk.Label(label="Backlight")
        title.add_css_class("page-title")
        title.set_halign(Gtk.Align.START)
        subtitle = Gtk.Label(label="Screenpad brightness and gamma correction")
        subtitle.add_css_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header.append(title)
        header.append(subtitle)
        self.append(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scroll)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.add_css_class("page-content")
        scroll.set_child(content)

        # ── Brightness ────────────────────────────────────────────────────
        bright_group = Adw.PreferencesGroup()
        bright_group.set_title("Screenpad Brightness")

        bright_row = Adw.ActionRow()
        bright_row.set_title("Brightness")
        bright_row.set_subtitle("0 = off, 100 = maximum")

        self._bright_slider = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 5
        )
        self._bright_slider.set_hexpand(True)
        self._bright_slider.set_draw_value(True)
        self._bright_slider.set_format_value_func(lambda _, v: f"{int(v)} %")
        self._bright_slider.add_css_class("backlight-slider")

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.set_valign(Gtk.Align.CENTER)
        apply_btn.connect("clicked", self._on_apply_brightness)

        bright_row.add_suffix(self._bright_slider)
        bright_row.add_suffix(apply_btn)
        bright_group.add(bright_row)

        # Sync toggle
        sync_row = Adw.ActionRow()
        sync_row.set_title("Sync with Primary Display")
        sync_row.set_subtitle("Screenpad follows the main display brightness")
        self._sync_switch = Gtk.Switch()
        self._sync_switch.set_valign(Gtk.Align.CENTER)
        self._sync_switch.connect("state-set", self._on_sync_toggled)
        sync_row.add_suffix(self._sync_switch)
        sync_row.set_activatable_widget(self._sync_switch)
        bright_group.add(sync_row)

        content.append(bright_group)

        # ── Gamma ─────────────────────────────────────────────────────────
        gamma_group = Adw.PreferencesGroup()
        gamma_group.set_title("Gamma")

        gamma_row = Adw.ActionRow()
        gamma_row.set_title("Screenpad Gamma")
        gamma_row.set_subtitle("0.5 = dark, 1.0 = linear, 2.2 = bright")

        self._gamma_slider = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0.5, 2.2, 0.1
        )
        self._gamma_slider.set_hexpand(True)
        self._gamma_slider.set_draw_value(True)
        self._gamma_slider.set_format_value_func(lambda _, v: f"{v:.1f}")
        self._gamma_slider.set_value(1.0)
        self._gamma_slider.add_mark(1.0, Gtk.PositionType.BOTTOM, "1.0")
        self._gamma_slider.add_css_class("backlight-slider")

        gamma_apply = Gtk.Button(label="Apply")
        gamma_apply.add_css_class("suggested-action")
        gamma_apply.set_valign(Gtk.Align.CENTER)
        gamma_apply.connect("clicked", self._on_apply_gamma)

        gamma_row.add_suffix(self._gamma_slider)
        gamma_row.add_suffix(gamma_apply)
        gamma_group.add(gamma_row)
        content.append(gamma_group)

    def _on_apply_brightness(self, _btn):
        val = int(self._bright_slider.get_value())

        def _set():
            try:
                asusctl._run("backlight", "--screenpad-brightness", str(val))
            except asusctl.AsusctlError:
                pass

        threading.Thread(target=_set, daemon=True).start()

    def _on_apply_gamma(self, _btn):
        val = round(self._gamma_slider.get_value(), 1)

        def _set():
            try:
                asusctl._run("backlight", "--screenpad-gamma", str(val))
            except asusctl.AsusctlError:
                pass

        threading.Thread(target=_set, daemon=True).start()

    def _on_sync_toggled(self, switch, state):
        def _set():
            try:
                asusctl._run(
                    "backlight",
                    "--sync-screenpad-brightness",
                    "true" if state else "false",
                )
            except asusctl.AsusctlError:
                pass

        threading.Thread(target=_set, daemon=True).start()
        return False  # allow the switch to update
