"""Keyboard illumination through UPower; no root GUI or direct sysfs writes."""
from .asusctl import AsusctlError


def _call(method: str, value: int | None = None):
    try:
        from gi.repository import Gio, GLib
    except ImportError as exc:
        raise AsusctlError("PyGObject não está instalado para este Python.") from exc
    try:
        connection = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        reply = connection.call_sync(
            "org.freedesktop.UPower", "/org/freedesktop/UPower/KbdBacklight",
            "org.freedesktop.UPower.KbdBacklight", method,
            GLib.Variant("(i)", (value,)) if value is not None else None,
            None, Gio.DBusCallFlags.NONE, 5000, None)
        return reply.unpack()
    except GLib.Error as exc:
        raise AsusctlError(f"Não foi possível acessar a iluminação do teclado: {exc}") from exc


def get_brightness() -> tuple[int, int]:
    maximum = _call("GetMaxBrightness")[0]
    current = _call("GetBrightness")[0]
    if maximum <= 0 or not 0 <= current <= maximum:
        raise AsusctlError("O UPower não informou níveis de brilho válidos.")
    return current, maximum


def set_brightness(value: int) -> None:
    maximum = _call("GetMaxBrightness")[0]
    if type(value) is not int or not 0 <= value <= maximum:
        raise AsusctlError("Nível de brilho inválido.")
    _call("SetBrightness", value)
