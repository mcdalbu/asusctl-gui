"""Adaptive Libadwaita shell; all hardware discovery happens off the UI thread."""
import threading
from pathlib import Path
from gi.repository import Adw, Gtk, Gdk, GLib, GObject
from .backend import system_info
from .pages.profile_page import ProfilePage
from .pages.battery_page import BatteryPage
from .pages.keyboard_page import KeyboardPage
from .pages.info_page import InfoPage


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("ASUS Control")
        self.set_default_size(960, 720)
        self.set_size_request(360, 480)
        self._closed = False
        self._probing = False
        self._pages = {}
        self.connect("close-request", self._on_close)
        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).with_name("style.css")))
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._split = Adw.OverlaySplitView()
        self._split.set_min_sidebar_width(200)
        self._split.set_max_sidebar_width(260)
        self.set_content(self._split)
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 680sp"))
        breakpoint.add_setter(self._split, "collapsed", True)
        self.add_breakpoint(breakpoint)

        sidebar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="ASUS Control", subtitle="Vivobook"))
        sidebar.add_top_bar(header)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._device = Gtk.Label(label="Identificando dispositivo…", wrap=True, xalign=0)
        self._device.add_css_class("device-label")
        box.append(self._device)
        self._nav = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self._nav.add_css_class("navigation-sidebar")
        self._nav.connect("row-selected", self._on_selected)
        box.append(self._nav)
        sidebar.set_content(box)
        self._split.set_sidebar(sidebar)

        content = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self._title = Adw.WindowTitle(title="ASUS Control")
        header.set_title_widget(self._title)
        navigation = Gtk.Button(icon_name="sidebar-show-symbolic", tooltip_text="Mostrar navegação")
        navigation.connect("clicked", lambda _: self._split.set_show_sidebar(True))
        self._split.bind_property("collapsed", navigation, "visible", GObject.BindingFlags.SYNC_CREATE)
        header.pack_start(navigation)
        self._refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Detectar recursos novamente")
        self._refresh.connect("clicked", lambda _: self._probe())
        header.pack_end(self._refresh)
        content.add_top_bar(header)
        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_vexpand(True)
        loading = Adw.StatusPage(title="Consultando o laptop", description="Detectando os controles disponíveis…")
        spinner = Gtk.Spinner(spinning=True, halign=Gtk.Align.CENTER)
        loading.set_child(spinner)
        self._stack.add_named(loading, "loading")
        content.set_content(self._stack)
        self._split.set_content(content)
        self._probe()

    def _on_close(self, _):
        self._closed = True
        for page in self._pages.values():
            page.dispose()
        return False

    def _probe(self):
        if self._probing or any(page._busy for page in self._pages.values()):
            return
        self._probing = True
        self._refresh.set_sensitive(False)
        self._stack.set_sensitive(False)
        def worker():
            info = system_info.reload()
            GLib.idle_add(self._populate, info)
        threading.Thread(target=worker, daemon=True).start()

    def _populate(self, info):
        if self._closed:
            return GLib.SOURCE_REMOVE
        previous = self._stack.get_visible_child_name()
        for page in self._pages.values():
            page.dispose()
            self._stack.remove(page)
        self._pages.clear()
        while self._nav.get_first_child():
            self._nav.remove(self._nav.get_first_child())
        self._device.set_label(info.product_family or info.product_name or "Laptop ASUS")
        if info.has_profiles:
            self._add_page("profile", "Energia", "power-profile-balanced-symbolic", ProfilePage())
        if info.has_battery_limit:
            self._add_page("battery", "Bateria", "battery-good-symbolic", BatteryPage())
        if info.has_keyboard:
            self._add_page("keyboard", "Teclado", "input-keyboard-symbolic", KeyboardPage())
        self._add_page("info", "Sistema", "computer-symbolic", InfoPage(info))
        selected = self._nav.get_row_at_index(0)
        index = 0
        while (row := self._nav.get_row_at_index(index)):
            if row.page_id == previous:
                selected = row
                break
            index += 1
        self._nav.select_row(selected)
        self._stack.set_sensitive(True)
        self._refresh.set_sensitive(True)
        self._probing = False
        return GLib.SOURCE_REMOVE

    def _add_page(self, page_id, title, icon, page):
        self._pages[page_id] = page
        self._stack.add_named(page, page_id)
        row = Gtk.ListBoxRow()
        row.page_id = page_id
        row.page_title = title
        box = Gtk.Box(spacing=12)
        box.append(Gtk.Image(icon_name=icon))
        box.append(Gtk.Label(label=title))
        row.set_child(box)
        self._nav.append(row)

    def _on_selected(self, _, row):
        if row:
            self._stack.set_visible_child_name(row.page_id)
            self._title.set_title(row.page_title)
            if self._split.get_collapsed():
                self._split.set_show_sidebar(False)
