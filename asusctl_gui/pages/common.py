"""Shared native preferences layout and background operation lifecycle."""
import threading
from gi.repository import Adw, Gtk, GLib


class ControlPage(Gtk.Box):
    def __init__(self, title, description):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._toast_overlay = Adw.ToastOverlay(vexpand=True)
        self.append(self._toast_overlay)
        self._busy = False
        self._disposed = False
        self._ready = False
        self._loading = False
        self.preferences = Adw.PreferencesPage(title=title)
        if self.preferences.find_property("description"):
            self.preferences.set_property("description", description)
        else:
            self.preferences.add(Adw.PreferencesGroup(description=description))
        self._toast_overlay.set_child(self.preferences)
        self._error_group = Adw.PreferencesGroup()
        self._error = Adw.ActionRow(title="Não foi possível concluir a operação")
        self._error.add_css_class("error")
        self._error.set_subtitle_lines(0)
        self._error_group.add(self._error)
        self._error_group.set_visible(False)
        self.preferences.add(self._error_group)
        self.controls = []
        self._refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Atualizar valores")
        self._refresh.set_valign(Gtk.Align.CENTER)
        self._refresh.connect("clicked", lambda _: self.refresh())
        self.controls.append(self._refresh)
        self._refresh.add_css_class("flat")

    def group(self, title, description=None):
        group = Adw.PreferencesGroup(title=title)
        if description:
            group.set_description(description)
        if self._refresh.get_parent() is None:
            group.set_header_suffix(self._refresh)
        self.preferences.add(group)
        return group

    def value_row(self, group, title):
        row = Adw.ActionRow(title=title)
        label = Gtk.Label(label="—", selectable=True, valign=Gtk.Align.CENTER)
        row.add_suffix(label)
        group.add(row)
        return label

    def button(self, row, label, callback, suggested=False):
        button = Gtk.Button(label=label, valign=Gtk.Align.CENTER)
        if suggested:
            button.add_css_class("suggested-action")
        button.connect("clicked", callback)
        row.add_suffix(button)
        self.controls.append(button)
        return button

    def dispose(self):
        self._disposed = True

    def run(self, operation, apply, message=None):
        if self._busy or self._disposed:
            return
        self._busy = True
        sensitivity = [c.get_sensitive() for c in self.controls]
        for control in self.controls:
            control.set_sensitive(False)
        self._error_group.set_visible(False)

        def finish(result, error):
            if self._disposed:
                return GLib.SOURCE_REMOVE
            self._busy = False
            for control, enabled in zip(self.controls, sensitivity):
                control.set_sensitive(enabled if self._ready else False)
            self._refresh.set_sensitive(True)
            if error:
                self._error.set_subtitle(GLib.markup_escape_text(str(error)))
                self._error_group.set_visible(True)
            else:
                if not self._ready:
                    for control in self.controls:
                        control.set_sensitive(True)
                self._ready = True
                self._loading = True
                try:
                    apply(result)
                finally:
                    self._loading = False
                if message:
                    self._toast_overlay.add_toast(Adw.Toast.new(message))
            return GLib.SOURCE_REMOVE

        def worker():
            try:
                result = operation()
            except Exception as exc:
                GLib.idle_add(finish, None, exc)
            else:
                GLib.idle_add(finish, result, None)
        threading.Thread(target=worker, daemon=True).start()
