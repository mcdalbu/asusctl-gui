"""
battery_page.py
───────────────
Battery charge limit controls and charge-mode selector.
"""

import threading
from gi.repository import Adw, Gtk, GLib
from ..backend import asusctl


CHARGE_MODE_LABELS = {
    "0": "Full Capacity",
    "1": "Balanced",
    "2": "Maximum Lifespan",
}

CHARGE_MODE_ICONS = {
    "0": "battery-full-symbolic",
    "1": "battery-good-symbolic",
    "2": "battery-low-symbolic",
}

CHARGE_MODE_DESCRIPTIONS = {
    "0": "Allows charging up to the set limit freely",
    "1": "Balanced charging for everyday use",
    "2": "Keeps the battery at lower charge to extend its life",
}


class BatteryPage(Gtk.Box):

    def __init__(self, has_armoury: bool = False, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)
        self._has_armoury = has_armoury
        self._suppress = False
        self._build()
        self.refresh()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header.add_css_class("page-header")
        title = Gtk.Label(label="Battery")
        title.add_css_class("page-title")
        title.set_halign(Gtk.Align.START)
        subtitle = Gtk.Label(label="Manage charge limits and charging strategy")
        subtitle.add_css_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_wrap(True)
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

        # ── Charge limit ──────────────────────────────────────────────────
        limit_group = Adw.PreferencesGroup()
        limit_group.set_title("Charge Limit")
        limit_group.set_description(
            "Maximum charge level to help preserve long-term battery health"
        )

        # Current value display
        self._limit_row = Adw.ActionRow()
        self._limit_row.set_title("Current Limit")
        self._limit_badge = Gtk.Label(label="…")
        self._limit_badge.add_css_class("limit-badge")
        self._limit_row.add_suffix(self._limit_badge)
        limit_group.add(self._limit_row)

        # Slider row
        slider_row = Adw.ActionRow()
        slider_row.set_title("Set Limit")
        slider_row.set_subtitle("Drag to set • 20 – 100 %")

        slider_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        slider_box.set_valign(Gtk.Align.CENTER)
        slider_box.set_hexpand(True)

        self._slider = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 20, 100, 5
        )
        self._slider.set_hexpand(True)
        self._slider.set_draw_value(True)
        self._slider.set_format_value_func(lambda _, v: f"{int(v)} %")
        self._slider.add_mark(60, Gtk.PositionType.BOTTOM, "60")
        self._slider.add_mark(80, Gtk.PositionType.BOTTOM, "80")
        self._slider.add_mark(100, Gtk.PositionType.BOTTOM, "100")
        self._slider.add_css_class("battery-slider")
        self._slider.connect("value-changed", self._on_slider_changed)

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.set_valign(Gtk.Align.CENTER)
        apply_btn.connect("clicked", self._on_apply_limit)

        slider_box.append(self._slider)
        slider_row.add_suffix(slider_box)
        slider_row.add_suffix(apply_btn)
        limit_group.add(slider_row)

        # One-shot row
        oneshot_row = Adw.ActionRow()
        oneshot_row.set_title("One-shot Full Charge")
        oneshot_row.set_subtitle(
            "Charge fully once, then revert to the configured limit"
        )
        oneshot_btn = Gtk.Button(label="Enable")
        oneshot_btn.add_css_class("pill")
        oneshot_btn.set_valign(Gtk.Align.CENTER)
        oneshot_btn.connect("clicked", self._on_oneshot)
        oneshot_row.add_suffix(oneshot_btn)
        limit_group.add(oneshot_row)

        content.append(limit_group)

        # ── Charge mode (armoury) ─────────────────────────────────────────
        if self._has_armoury:
            mode_group = Adw.PreferencesGroup()
            mode_group.set_title("Charging Mode")
            mode_group.set_description(
                "Strategy used by the firmware when determining how to charge"
            )

            self._mode_rows: dict[str, Adw.ActionRow] = {}
            self._mode_buttons: dict[str, Gtk.CheckButton] = {}
            last_btn = None

            for key in sorted(CHARGE_MODE_LABELS):
                label = CHARGE_MODE_LABELS[key]
                desc = CHARGE_MODE_DESCRIPTIONS[key]
                icon = CHARGE_MODE_ICONS[key]

                row = Adw.ActionRow()
                row.set_title(label)
                row.set_subtitle(desc)

                img = Gtk.Image.new_from_icon_name(icon)
                img.add_css_class("charge-mode-icon")
                row.add_prefix(img)

                btn = Gtk.CheckButton()
                btn.set_valign(Gtk.Align.CENTER)
                if last_btn:
                    btn.set_group(last_btn)
                last_btn = btn
                btn.connect("toggled", self._on_mode_toggled, key)

                row.add_suffix(btn)
                row.set_activatable_widget(btn)

                self._mode_rows[key] = row
                self._mode_buttons[key] = btn
                mode_group.add(row)

            content.append(mode_group)

        # ── Refresh ───────────────────────────────────────────────────────
        refresh_group = Adw.PreferencesGroup()
        refresh_row = Adw.ActionRow()
        refresh_row.set_title("Refresh")
        refresh_row.set_subtitle("Re-read battery state from asusd")
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.add_css_class("flat")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.connect("clicked", lambda _: self.refresh())
        refresh_row.add_suffix(refresh_btn)
        refresh_group.add(refresh_row)
        content.append(refresh_group)

    # ── Refresh ────────────────────────────────────────────────────────────

    def refresh(self):
        def _fetch():
            limit = asusctl.get_battery_limit()
            attrs = asusctl.get_armoury_attributes() if self._has_armoury else {}
            return limit, attrs

        def _apply(result):
            limit, attrs = result
            self._suppress = True

            # Limit
            self._limit_badge.set_label(f"{limit} %")
            self._slider.set_value(limit)
            # Color badge by limit
            self._limit_badge.remove_css_class("badge-green")
            self._limit_badge.remove_css_class("badge-yellow")
            self._limit_badge.remove_css_class("badge-red")
            if limit <= 60:
                self._limit_badge.add_css_class("badge-green")
            elif limit <= 80:
                self._limit_badge.add_css_class("badge-yellow")
            else:
                self._limit_badge.add_css_class("badge-red")

            # Charge mode
            if self._has_armoury and "charge_mode" in attrs:
                cur = attrs["charge_mode"].get("current", "0")
                for key, btn in self._mode_buttons.items():
                    btn.set_active(key == cur)

            self._suppress = False

        threading.Thread(
            target=lambda: GLib.idle_add(_apply, _fetch()), daemon=True
        ).start()

    # ── Handlers ───────────────────────────────────────────────────────────

    def _on_slider_changed(self, slider):
        # Live update badge while dragging
        val = int(slider.get_value())
        self._limit_badge.set_label(f"{val} %")

    def _on_apply_limit(self, _btn):
        limit = int(self._slider.get_value())

        def _set():
            try:
                asusctl.set_battery_limit(limit)
                GLib.idle_add(self.refresh)
            except asusctl.AsusctlError:
                pass

        threading.Thread(target=_set, daemon=True).start()

    def _on_oneshot(self, _btn):
        def _do():
            try:
                asusctl.battery_oneshot()
            except asusctl.AsusctlError:
                pass

        threading.Thread(target=_do, daemon=True).start()

    def _on_mode_toggled(self, btn: Gtk.CheckButton, key: str):
        if self._suppress or not btn.get_active():
            return

        def _set():
            try:
                asusctl.set_armoury_attribute("charge_mode", key)
            except asusctl.AsusctlError:
                GLib.idle_add(self.refresh)

        threading.Thread(target=_set, daemon=True).start()
