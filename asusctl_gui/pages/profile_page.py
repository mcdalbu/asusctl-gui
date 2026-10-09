from gi.repository import Adw, Gtk
from ..backend import asusctl, platform
from .common import ControlPage

PROFILE_META = {
    "Quiet": ("Silencioso", "Prioriza menor ruído e consumo", "weather-clear-night-symbolic"),
    "Balanced": ("Equilibrado", "Equilíbrio entre desempenho e consumo", "power-profile-balanced-symbolic"),
    "Performance": ("Desempenho", "Prioriza desempenho; pode aumentar o ruído e o consumo", "power-profile-performance-symbolic"),
}


def display(profile):
    return PROFILE_META.get(profile, ("—",))[0]


class ProfilePage(ControlPage):
    def __init__(self):
        super().__init__("Energia", "Controle os perfis térmicos e de desempenho do seu Vivobook.")
        self._available = []
        group = self.group("Estado atual")
        self._active = self.value_row(group, "Perfil ativo")
        self._ac = self.value_row(group, "Ao conectar à tomada")
        self._battery = self.value_row(group, "Ao usar a bateria")
        group = self.group("Selecionar perfil")
        self._buttons = {}
        for profile, (title, description, icon) in PROFILE_META.items():
            row = Adw.ActionRow(title=title, subtitle=description)
            row.add_prefix(Gtk.Image(icon_name=icon))
            self._buttons[profile] = self.button(row, "Ativar", lambda _, p=profile: self.activate(p))
            group.add(row)
        group = self.group("Perfis automáticos", "Ative a alternância desejada e clique em Salvar. O asusd gerencia as mudanças da fonte de energia.")
        self._combos = {}
        self._auto_buttons = {}
        self._switches = {}
        for source, title in (("ac", "Na tomada"), ("battery", "Na bateria")):
            row = Adw.ComboRow(title=title)
            group.add(row)
            switch = Adw.SwitchRow(title=f"Alternar automaticamente: {title.lower()}")
            group.add(switch)
            self._switches[source] = switch
            self.controls.append(switch)
            self._combos[source] = row
            self.controls.append(row)
            action = Adw.ActionRow(title=f"Salvar perfil: {title.lower()}")
            self._auto_buttons[source] = self.button(action, "Salvar", lambda _, s=source: self.save_auto(s))
            group.add(action)
        self.refresh()

    @staticmethod
    def _fetch():
        data = asusctl.get_profiles()
        data.update(platform.get_auto_profiles_enabled())
        return data

    def refresh(self):
        self.run(self._fetch, self._apply)

    def _apply(self, data):
        self._available = data["available"]
        self._active.set_label(display(data["active"]))
        for source, label in (("ac", self._ac), ("battery", self._battery)):
            enabled = data.get(f"{source}_enabled")
            state = "ativado" if enabled else "desativado"
            if enabled is None:
                state = "estado indisponível"
            label.set_label(f"{display(data[source])} ({state})")
        for profile, button in self._buttons.items():
            button.set_sensitive(profile in self._available and profile != data["active"])
            button.set_label("Ativo" if profile == data["active"] else "Ativar")
        for source, combo in self._combos.items():
            combo.set_model(Gtk.StringList.new([display(p) for p in self._available]))
            configured = data[source] in self._available
            combo.set_selected(self._available.index(data[source]) if configured else Gtk.INVALID_LIST_POSITION)
            combo.set_sensitive(configured)
            enabled = data.get(f"{source}_enabled")
            self._switches[source].set_active(enabled is True)
            self._switches[source].set_sensitive(configured and enabled is not None)
            self._auto_buttons[source].set_sensitive(configured and enabled is not None)

    def activate(self, profile):
        def operation():
            asusctl.set_profile(profile)
            data = self._fetch()
            if data["active"] != profile:
                raise asusctl.AsusctlError("O sistema não confirmou o perfil solicitado. Atualize os valores.")
            return data
        self.run(operation, self._apply, "Perfil atualizado")

    def save_auto(self, source):
        index = self._combos[source].get_selected()
        if index >= len(self._available):
            return
        profile = self._available[index]
        enabled = self._switches[source].get_active()
        def operation():
            asusctl.set_profile(profile, source)
            platform.set_auto_profile_enabled(source, enabled)
            data = self._fetch()
            if data[source] != profile or data.get(f"{source}_enabled") != enabled:
                raise asusctl.AsusctlError("O sistema não confirmou o perfil automático. Atualize os valores.")
            return data
        self.run(operation, self._apply, "Perfil automático salvo")
