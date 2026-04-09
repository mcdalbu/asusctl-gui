"""
info_page.py
────────────
Displays system / asusctl version info and supported features.
"""

from gi.repository import Adw, Gtk, GLib
from ..backend.asusctl import SystemInfo


class InfoPage(Gtk.Box):

    def __init__(self, info: SystemInfo, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)
        self._info = info
        self._build()

    def _build(self):
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header.add_css_class("page-header")
        title = Gtk.Label(label="About")
        title.add_css_class("page-title")
        title.set_halign(Gtk.Align.START)
        subtitle = Gtk.Label(label="System info and supported asusd features")
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

        # ── Device info ───────────────────────────────────────────────────
        device_group = Adw.PreferencesGroup()
        device_group.set_title("Device")

        def _info_row(title, value):
            row = Adw.ActionRow()
            row.set_title(title)
            lbl = Gtk.Label(label=value or "—")
            lbl.add_css_class("dim-label")
            lbl.set_selectable(True)
            row.add_suffix(lbl)
            return row

        device_group.add(_info_row("Product Family", self._info.product_family))
        device_group.add(_info_row("Board Name", self._info.board_name))
        device_group.add(_info_row("asusctl Version", self._info.asusctl_version))
        content.append(device_group)

        # ── Supported interfaces ──────────────────────────────────────────
        iface_group = Adw.PreferencesGroup()
        iface_group.set_title("Active D-Bus Interfaces")
        if self._info.supported_interfaces:
            for iface in self._info.supported_interfaces:
                row = Adw.ActionRow()
                row.set_title(iface.split(".")[-1])
                row.set_subtitle(iface)
                dot = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                dot.add_css_class("success-color")
                row.add_prefix(dot)
                iface_group.add(row)
        else:
            row = Adw.ActionRow()
            row.set_title("No interfaces reported")
            iface_group.add(row)
        content.append(iface_group)

        # ── Feature availability ──────────────────────────────────────────
        feat_group = Adw.PreferencesGroup()
        feat_group.set_title("Feature Support")

        features = [
            ("Power Profiles", True),
            ("Battery Limit", True),
            ("Armoury / Firmware Attrs", self._info.has_armoury),
            ("Backlight / Screenpad", self._info.has_backlight),
            ("Fan Curves", self._info.has_fan_curves),
            ("Aura LEDs", self._info.has_aura),
        ]
        for name, supported in features:
            row = Adw.ActionRow()
            row.set_title(name)
            if supported:
                icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                icon.add_css_class("success-color")
                lbl = Gtk.Label(label="Supported")
                lbl.add_css_class("success-color")
            else:
                icon = Gtk.Image.new_from_icon_name("action-unavailable-symbolic")
                icon.add_css_class("dim-label")
                lbl = Gtk.Label(label="Not available")
                lbl.add_css_class("dim-label")
            row.add_prefix(icon)
            row.add_suffix(lbl)
            feat_group.add(row)

        content.append(feat_group)

        # ── App info ──────────────────────────────────────────────────────
        app_group = Adw.PreferencesGroup()
        app_group.set_title("Application")
        app_group.add(_info_row("asusctl-gui version", "1.0.0"))
        app_group.add(_info_row("Homepage", "https://asus-linux.org"))
        content.append(app_group)
