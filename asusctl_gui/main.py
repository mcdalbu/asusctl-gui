"""
main.py
───────
Application entry point.  Initialise a Gtk.Application with Adwaita
style manager and an application ID appropriate for polkit rules.
"""

import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gio, GLib

from .window import MainWindow


APP_ID = "org.asuslinux.AsusctlGui"
APP_VERSION = "1.0.0"


class AsusctlGuiApp(Adw.Application):

    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app):
        # Follow system colour scheme
        style_mgr = Adw.StyleManager.get_default()
        style_mgr.set_color_scheme(Adw.ColorScheme.DEFAULT)

        win = MainWindow(application=self)
        win.present()


def main():
    app = AsusctlGuiApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
