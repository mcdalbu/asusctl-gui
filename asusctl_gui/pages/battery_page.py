from gi.repository import Adw, Gtk
from ..backend import asusctl
from .common import ControlPage

STATUS = {"Charging": "Carregando", "Discharging": "Descarregando", "Full": "Carga completa",
          "Not charging": "Sem carregar", "Unknown": "Desconhecido"}


class BatteryPage(ControlPage):
    def __init__(self):
        super().__init__("Bateria", "Defina até onde a bateria pode carregar.")
        group = self.group("Estado da bateria")
        self._capacity = self.value_row(group, "Carga atual")
        self._status = self.value_row(group, "Situação")
        self._limit = self.value_row(group, "Limite aplicado")
        group = self.group("Limite de carga", "O valor só é enviado ao sistema quando você clica em Aplicar.")
        self._slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 20, 100, 1)
        self._slider.set_draw_value(True)
        self._slider.set_format_value_func(lambda _, value: f"{int(value)}%")
        self._slider.set_margin_top(12)
        self._slider.set_margin_bottom(12)
        self._slider.set_sensitive(False)
        self.controls.append(self._slider)
        for value in (60, 80, 100):
            self._slider.add_mark(value, Gtk.PositionType.BOTTOM, str(value))
        slider_row = Gtk.ListBoxRow(activatable=False, selectable=False)
        self._slider.set_margin_start(16)
        self._slider.set_margin_end(16)
        self._slider.update_property([Gtk.AccessibleProperty.LABEL], ["Limite de carga em porcentagem"])
        slider_row.set_child(self._slider)
        group.add(slider_row)
        row = Adw.ActionRow(title="Novo limite", subtitle="De 20 a 100%")
        self._apply_button = self.button(row, "Aplicar", self._on_apply, True)
        self._apply_button.set_sensitive(False)
        group.add(row)
        preset = Adw.ActionRow(title="Atalhos")
        for value in (60, 80, 100):
            self.button(preset, f"{value}%", lambda _, v=value: self._slider.set_value(v))
        group.add(preset)
        group = self.group("Carga temporária")
        row = Adw.ActionRow(title="Carregar até 100% uma vez", subtitle="O asusd gerencia o retorno ao limite configurado")
        group.add(row)
        self.button(row, "Ativar", self._oneshot)
        self.refresh()

    @staticmethod
    def _fetch():
        return asusctl.get_battery_limit(), asusctl.get_battery_status()

    def _apply(self, data):
        limit, state = data
        self._limit.set_label(f"{limit}%")
        self._slider.set_value(limit)
        self._capacity.set_label(f'{state["capacity"]}%' if state["capacity"] is not None else "—")
        self._status.set_label(STATUS.get(state["status"], state["status"] or "—"))

    def refresh(self):
        self.run(self._fetch, self._apply)

    def _on_apply(self, _):
        value = int(self._slider.get_value())
        def operation():
            asusctl.set_battery_limit(value)
            data = self._fetch()
            if data[0] != value:
                raise asusctl.AsusctlError("O sistema não confirmou o limite solicitado. Atualize os valores.")
            return data
        self.run(operation, self._apply, "Limite de carga atualizado")

    def _oneshot(self, _):
        def operation():
            asusctl.battery_oneshot()
            return self._fetch()
        self.run(operation, self._apply, "Carga temporária ativada")
