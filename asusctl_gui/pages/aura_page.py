"""
aura_page.py
────────────
Keyboard backlight (Aura) effect selection page.
"""

import threading
from gi.repository import Adw, Gtk, GLib
from ..backend import asusctl


AURA_EFFECTS = {
    "static": ("Static", "Static single-colour effect"),
    "breathe": ("Breathe", "Breathing effect"),
    "rainbow-cycle": ("Rainbow Cycle", "Smooth color cycling"),
    "stars": ("Stars", "Star effect"),
    "rain": ("Rain", "Rainfall effect"),
    "highlight": ("Highlight", "Highlight effect"),
    "laser": ("Laser", "Laser beam effect"),
    "ripple": ("Ripple", "Water ripple effect"),
    "pulse": ("Pulse", "Single-colour pulse effect"),
    "comet": ("Comet", "Comet effect"),
    "flash": ("Flash", "Flashing effect"),
}


class AuraPage(Gtk.Box):
    """Page to set the hardware aura effect."""

    def __init__(self, has_aura: bool = False, **kwargs):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            **kwargs,
        )
        self._has_aura = has_aura
        self._build_ui()

    def _build_ui(self):
        # ── Header ─────────────────────────────────────────────────────────
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header.add_css_class("page-header")

        title = Gtk.Label(label="Keyboard Aura")
        title.add_css_class("page-title")
        title.set_halign(Gtk.Align.START)

        subtitle = Gtk.Label(
            label="Configure keyboard backlight effects and animations"
        )
        subtitle.add_css_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_wrap(True)

        header.append(title)
        header.append(subtitle)
        self.append(header)

        # ── Content ────────────────────────────────────────────────────────
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scroll)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.add_css_class("page-content")
        scroll.set_child(content)

        if not self._has_aura:
            status = Adw.StatusPage()
            status.set_title("Aura Not Detected")
            status.set_icon_name("software-update-available-symbolic")
            status.set_description(
                "Aura LED control requires a supported ASUS laptop and necessary dependencies.\n\n"
                "To ensure it works on compatible models:\n"
                "1. Check if 'asusd' is installed and running:\n"
                "   sudo systemctl enable --now asusd\n"
                "2. Install ASUS Linux extensions via Copr if needed:\n"
                "   sudo dnf copr enable lukejones/asus-linux\n"
                "   sudo dnf reinstall asusctl\n"
                "3. Ensure your kernel supports 'hid-asus' modules."
            )
            content.append(status)
            return

        # ── Effects List ───────────────────────────────────────────────────
        effects_group = Adw.PreferencesGroup()
        effects_group.set_title("Animations")
        effects_group.set_description("Select an effect. Not all hardware supports every effect.")

        for effect_id, (label, desc) in AURA_EFFECTS.items():
            row = Adw.ActionRow()
            row.set_title(label)
            row.set_subtitle(desc)

            btn = Gtk.Button(label="Apply")
            btn.add_css_class("pill")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", self._make_apply_handler(effect_id))

            row.add_suffix(btn)
            row.set_activatable_widget(btn)

            effects_group.add(row)

        content.append(effects_group)

    def _make_apply_handler(self, effect_id: str):
        def _on_click(_btn):
            def _do():
                try:
                    asusctl.set_aura_effect(effect_id)
                except asusctl.AsusctlError:
                    pass
            threading.Thread(target=_do, daemon=True).start()
        return _on_click
