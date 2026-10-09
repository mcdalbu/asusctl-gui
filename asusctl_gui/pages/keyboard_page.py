from gi.repository import Adw, Gtk
from ..backend import keyboard
from ..backend.asusctl import AsusctlError
from .common import ControlPage


class KeyboardPage(ControlPage):
    def __init__(self):
        super().__init__("Teclado", "Ajuste a intensidade da iluminação do teclado.")
        self._maximum = 0
        group = self.group("Iluminação", "As teclas de brilho do laptop continuam funcionando. Use Atualizar para consultar mudanças.")
        self._current = self.value_row(group, "Nível aplicado")
        self._slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self._slider.set_draw_value(True)
        self._slider.set_digits(0)
        self._slider.set_margin_top(12)
        self._slider.set_margin_bottom(12)
        slider_row = Gtk.ListBoxRow(activatable=False, selectable=False)
        self._slider.set_margin_start(16)
        self._slider.set_margin_end(16)
        self._slider.update_property([Gtk.AccessibleProperty.LABEL], ["Nível de iluminação do teclado"])
        slider_row.set_child(self._slider)
        group.add(slider_row)
        self.controls.append(self._slider)
        row = Adw.ActionRow(title="Novo nível", subtitle="0 desliga a iluminação")
        self._button = self.button(row, "Aplicar", self._on_apply, True)
        group.add(row)
        self.refresh()

    def _apply(self, data):
        current, self._maximum = data
        self._current.set_label(f"{current} / {self._maximum}")
        self._slider.set_range(0, self._maximum)
        self._slider.set_value(current)

    def refresh(self):
        self.run(keyboard.get_brightness, self._apply)

    def _on_apply(self, _):
        value = int(self._slider.get_value())
        def operation():
            keyboard.set_brightness(value)
            data = keyboard.get_brightness()
            if data[0] != value:
                raise AsusctlError("O sistema não confirmou o brilho solicitado. Atualize os valores.")
            return data
        self.run(operation, self._apply, "Iluminação atualizada")
