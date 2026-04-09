"""
profile_page.py
───────────────
Page for selecting the platform throttle policy (Quiet / Balanced / Performance).
"""

from gi.repository import Adw, Gtk, GLib, Gio
from ..backend import asusctl


# Profile config: name → (icon, description, accent CSS class)
PROFILE_META = {
    "Quiet": (
        "audio-volume-low-symbolic",
        "Minimal noise. Reduced CPU/GPU power for silent operation.",
        "profile-quiet",
    ),
    "Balanced": (
        "emoji-nature-symbolic",
        "Balanced performance and efficiency for everyday tasks.",
        "profile-balanced",
    ),
    "Performance": (
        "thunderbolt-symbolic",
        "Maximum CPU and GPU performance. Higher power draw.",
        "profile-performance",
    ),
}


class ProfilePage(Gtk.Box):
    """Power profile selection page."""

    def __init__(self, **kwargs):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            **kwargs,
        )
        self._buttons: dict[str, Gtk.CheckButton] = {}
        self._loading = False

        self._build_ui()
        self.refresh()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header bar ────────────────────────────────────────────────────
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header.add_css_class("page-header")

        title = Gtk.Label(label="Power Profile")
        title.add_css_class("page-title")
        title.set_halign(Gtk.Align.START)

        subtitle = Gtk.Label(
            label="Controls the platform throttle policy managed by asusd"
        )
        subtitle.add_css_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_wrap(True)

        header.append(title)
        header.append(subtitle)
        self.append(header)

        # ── Scroll container ───────────────────────────────────────────────
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scroll)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.add_css_class("page-content")
        scroll.set_child(content)

        # ── Status banner ─────────────────────────────────────────────────
        self._status_row = Adw.ActionRow()
        self._status_row.set_title("Current Profile")
        self._status_row.add_css_class("status-card")

        self._status_label = Gtk.Label(label="…")
        self._status_label.add_css_class("status-value")
        self._status_row.add_suffix(self._status_label)

        status_group = Adw.PreferencesGroup()
        status_group.set_title("Status")
        status_group.add(self._status_row)

        self._ac_row = Adw.ActionRow()
        self._ac_row.set_title("AC Power Profile")
        self._ac_label = Gtk.Label(label="…")
        self._ac_label.add_css_class("dim-label")
        self._ac_row.add_suffix(self._ac_label)
        status_group.add(self._ac_row)

        self._bat_row = Adw.ActionRow()
        self._bat_row.set_title("Battery Profile")
        self._bat_label = Gtk.Label(label="…")
        self._bat_label.add_css_class("dim-label")
        self._bat_row.add_suffix(self._bat_label)
        status_group.add(self._bat_row)

        content.append(status_group)

        # ── Profile cards ─────────────────────────────────────────────────
        cards_group = Adw.PreferencesGroup()
        cards_group.set_title("Select Profile")

        last_btn = None
        for profile, (icon, desc, css_class) in PROFILE_META.items():
            row = Adw.ActionRow()
            row.set_title(profile)
            row.set_subtitle(desc)
            row.add_css_class("profile-row")

            icon_img = Gtk.Image.new_from_icon_name(icon)
            icon_img.add_css_class("profile-icon")
            icon_img.add_css_class(f"profile-icon-{css_class.split('-')[-1]}")
            row.add_prefix(icon_img)

            btn = Gtk.CheckButton()
            btn.set_valign(Gtk.Align.CENTER)
            if last_btn is not None:
                btn.set_group(last_btn)
            last_btn = btn
            btn.connect("toggled", self._on_profile_toggled, profile)

            row.add_suffix(btn)
            row.set_activatable_widget(btn)

            self._buttons[profile] = btn
            cards_group.add(row)

        content.append(cards_group)

        # ── Next Profile button ────────────────────────────────────────────
        actions_group = Adw.PreferencesGroup()
        actions_group.set_title("Actions")

        next_row = Adw.ActionRow()
        next_row.set_title("Cycle Profile")
        next_row.set_subtitle("Rotate to the next profile in sequence")

        next_btn = Gtk.Button(label="Next →")
        next_btn.add_css_class("suggested-action")
        next_btn.set_valign(Gtk.Align.CENTER)
        next_btn.connect("clicked", self._on_next_clicked)
        next_row.add_suffix(next_btn)

        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.add_css_class("flat")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.set_tooltip_text("Refresh")
        refresh_btn.connect("clicked", lambda _: self.refresh())
        next_row.add_suffix(refresh_btn)

        actions_group.add(next_row)
        content.append(actions_group)

        # ── Toast overlay for feedback ─────────────────────────────────────
        self._toast_overlay = Adw.ToastOverlay()

    # ── Refresh ────────────────────────────────────────────────────────────

    def refresh(self):
        """Load current profile state from asusctl in a background thread."""
        def _fetch():
            try:
                return asusctl.get_profiles()
            except asusctl.AsusctlError:
                return None

        def _apply(data):
            if data is None:
                return
            self._loading = True
            active = data.get("active", "Balanced")
            ac = data.get("ac", "")
            bat = data.get("battery", "")

            self._status_label.set_label(active)
            self._ac_label.set_label(ac or "—")
            self._bat_label.set_label(bat or "—")

            for name, btn in self._buttons.items():
                btn.set_active(name == active)
            self._loading = False

        import threading
        t = threading.Thread(target=lambda: GLib.idle_add(_apply, _fetch()), daemon=True)
        t.start()

    # ── Handlers ───────────────────────────────────────────────────────────

    def _on_profile_toggled(self, btn: Gtk.CheckButton, profile: str):
        if self._loading or not btn.get_active():
            return

        def _set():
            try:
                asusctl.set_profile(profile)
                GLib.idle_add(self.refresh)
            except asusctl.AsusctlError as e:
                GLib.idle_add(self._show_error, str(e))

        import threading
        threading.Thread(target=_set, daemon=True).start()

    def _on_next_clicked(self, _btn):
        def _next():
            try:
                asusctl.next_profile()
                GLib.idle_add(self.refresh)
            except asusctl.AsusctlError as e:
                GLib.idle_add(self._show_error, str(e))

        import threading
        threading.Thread(target=_next, daemon=True).start()

    def _show_error(self, msg: str):
        toast = Adw.Toast.new(f"Error: {msg}")
        toast.set_timeout(4)
