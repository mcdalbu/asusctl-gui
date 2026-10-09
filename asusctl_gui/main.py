"""Application entry point for the native GTK4/Libadwaita interface."""
import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio
from .window import MainWindow

APP_ID = "org.asuslinux.AsusctlGui"


class AsusctlGuiApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect("activate", self._on_activate)

    def _on_activate(self, _):
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)
        window = self.get_active_window()
        if window is None:
            window = MainWindow(application=self)
        window.present()


def main():
    return AsusctlGuiApp().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
