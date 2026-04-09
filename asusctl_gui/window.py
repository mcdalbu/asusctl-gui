"""
window.py
─────────
Main application window.
Left sidebar with navigation list + right content stack.
"""

import os
from gi.repository import Adw, Gtk, Gdk, GLib

from .backend import system_info
from .pages.profile_page import ProfilePage
from .pages.battery_page import BatteryPage
from .pages.info_page import InfoPage
from .pages.backlight_page import BacklightPage
from .pages.aura_page import AuraPage


class MainWindow(Adw.ApplicationWindow):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title("asusctl-gui")
        self.set_default_size(880, 620)
        self.set_size_request(640, 480)

        # Load CSS
        self._load_css()

        # Probe system once
        self._info = system_info.load()

        # Build layout
        self._pages: dict[str, Gtk.Widget] = {}
        self._build()

    # ── CSS ───────────────────────────────────────────────────────────────

    def _load_css(self):
        css_path = os.path.join(os.path.dirname(__file__), "style.css")
        if os.path.exists(css_path):
            provider = Gtk.CssProvider()
            provider.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        # Native ToolbarView with HeaderBar for window controls
        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        
        # Root split pane
        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        toolbar_view.set_content(split)
        
        self.set_content(toolbar_view)

        # ── Sidebar ────────────────────────────────────────────────────────
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.add_css_class("main-sidebar")
        split.append(sidebar)

        # Logo / brand strip
        logo_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        logo_box.add_css_class("sidebar-logo")

        logo_title = Gtk.Label(label="asusctl")
        logo_title.add_css_class("sidebar-logo-title")
        logo_title.set_halign(Gtk.Align.START)
        logo_box.append(logo_title)

        logo_sub = Gtk.Label(label="ROG CONTROL")
        logo_sub.add_css_class("sidebar-logo-sub")
        logo_sub.set_halign(Gtk.Align.START)
        logo_box.append(logo_sub)

        # Device name
        dev_label = Gtk.Label(
            label=self._info.product_family or "ASUS Laptop"
        )
        dev_label.add_css_class("dim-label")
        dev_label.set_halign(Gtk.Align.START)
        dev_label.set_margin_top(4)
        logo_box.append(dev_label)

        sidebar.append(logo_box)

        # Nav list
        nav_scroll = Gtk.ScrolledWindow()
        nav_scroll.set_vexpand(True)
        nav_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar.append(nav_scroll)

        self._nav_list = Gtk.ListBox()
        self._nav_list.add_css_class("navigation-sidebar")
        self._nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._nav_list.connect("row-selected", self._on_nav_selected)
        nav_scroll.set_child(self._nav_list)

        # ── Content area ───────────────────────────────────────────────────
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_transition_duration(200)
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)
        split.append(self._stack)

        # ── Register pages ─────────────────────────────────────────────────
        self._add_page(
            "profile",
            "Profile",
            "thunderbolt-symbolic",
            ProfilePage(),
        )
        self._add_page(
            "battery",
            "Battery",
            "battery-good-symbolic",
            BatteryPage(has_armoury=self._info.has_armoury),
        )
        if self._info.has_backlight:
            self._add_page(
                "backlight",
                "Backlight",
                "display-brightness-symbolic",
                BacklightPage(),
            )
        self._add_page(
            "aura",
            "Keyboard Aura",
            "keyboard-brightness-symbolic",
            AuraPage(has_aura=self._info.has_aura),
        )
        self._add_page(
            "info",
            "About",
            "help-about-symbolic",
            InfoPage(info=self._info),
        )

        # Select first page
        first_row = self._nav_list.get_row_at_index(0)
        if first_row:
            self._nav_list.select_row(first_row)

    # ── Nav helpers ────────────────────────────────────────────────────────

    def _add_page(self, page_id: str, label: str, icon_name: str, widget: Gtk.Widget):
        # Add to stack
        self._stack.add_named(widget, page_id)
        self._pages[page_id] = widget

        # Create sidebar row
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row_box.set_margin_top(2)
        row_box.set_margin_bottom(2)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.add_css_class("nav-icon")
        icon.set_pixel_size(18)
        row_box.append(icon)

        lbl = Gtk.Label(label=label)
        lbl.set_halign(Gtk.Align.START)
        row_box.append(lbl)

        row = Gtk.ListBoxRow()
        row.add_css_class("nav-row")
        row.set_child(row_box)
        # Store page id for lookup
        row._page_id = page_id  # type: ignore[attr-defined]

        self._nav_list.append(row)

    def _on_nav_selected(self, _listbox, row):
        if row is None:
            return
        page_id = getattr(row, "_page_id", None)
        if page_id:
            self._stack.set_visible_child_name(page_id)
