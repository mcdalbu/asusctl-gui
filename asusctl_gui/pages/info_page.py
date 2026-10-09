from gi.repository import Adw, Gtk, GLib
from .. import __version__
from .common import ControlPage


class InfoPage(ControlPage):
    def __init__(self, info):
        super().__init__("Sistema", "Identificação do laptop e recursos disponíveis nesta instalação.")
        self._refresh.set_visible(False)
        group = self.group("Dispositivo")
        for title, value in (("Modelo", info.product_name), ("Família", info.product_family),
                             ("Placa", info.board_name), ("Kernel", info.kernel),
                             ("asusctl", info.asusctl_version), ("ASUS Control", __version__)):
            row = Adw.ActionRow(title=title, subtitle=GLib.markup_escape_text(value) if value else "Não informado")
            row.set_subtitle_selectable(True)
            group.add(row)
        group = self.group("Recursos detectados", "O suporte depende do hardware, do firmware, do kernel e dos serviços instalados.")
        for title, available in (("Perfis de energia", info.has_profiles),
                                 ("Limite de carga", info.has_battery_limit),
                                 ("Brilho do teclado (UPower)", info.has_keyboard),
                                 ("Aura RGB (asusd)", info.has_aura),
                                 ("Curvas de ventoinha (asusd)", info.has_fan_curves),
                                 ("Atributos Armoury (asusd)", info.has_armoury)):
            row = Adw.ActionRow(title=title, subtitle="Disponível" if available else "Não disponível nesta instalação")
            row.add_prefix(Gtk.Image(icon_name="emblem-ok-symbolic" if available else "action-unavailable-symbolic"))
            group.add(row)
        if info.error:
            group = self.group("Conexão com o asusd")
            row = Adw.ActionRow(title="Não foi possível consultar o serviço", subtitle=GLib.markup_escape_text(info.error))
            row.set_subtitle_selectable(True)
            group.add(row)
        group = self.group("Diagnóstico")
        buffer = Gtk.TextBuffer()
        buffer.set_text(info.raw or info.error or "Sem informações do asusd")
        text = Gtk.TextView(buffer=buffer, editable=False, cursor_visible=False,
                            monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        text.set_margin_top(12)
        text.set_margin_bottom(12)
        group.add(text)

    def refresh(self):
        pass
