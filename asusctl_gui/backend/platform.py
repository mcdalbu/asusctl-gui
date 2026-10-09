"""Platform properties not exposed as setters by the asusctl CLI."""
from .asusctl import AsusctlError

PROPERTIES = {'ac': 'ChangePlatformProfileOnAc', 'battery': 'ChangePlatformProfileOnBattery'}


def _property(source: str, value: bool | None = None):
    if source not in PROPERTIES:
        raise AsusctlError('Fonte de energia inválida.')
    try:
        from gi.repository import Gio, GLib
    except ImportError as exc:
        raise AsusctlError('PyGObject não está instalado para este Python.') from exc
    try:
        connection = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        prop = PROPERTIES[source]
        if value is None:
            args = GLib.Variant('(ss)', ('xyz.ljones.Platform', prop))
            method = 'Get'
        else:
            args = GLib.Variant('(ssv)', ('xyz.ljones.Platform', prop, GLib.Variant('b', value)))
            method = 'Set'
        reply = connection.call_sync('xyz.ljones.Asusd', '/xyz/ljones',
                                     'org.freedesktop.DBus.Properties', method, args,
                                     None, Gio.DBusCallFlags.NONE, 5000, None)
        return reply.unpack()[0] if value is None else None
    except GLib.Error as exc:
        raise AsusctlError(f'Não foi possível acessar os perfis automáticos: {exc}') from exc


def get_auto_profiles_enabled() -> dict:
    result = {}
    for source in PROPERTIES:
        try:
            result[f'{source}_enabled'] = bool(_property(source))
        except AsusctlError:
            # An older daemon may lack this property. Do not claim it is enabled.
            result[f'{source}_enabled'] = None
    return result


def set_auto_profile_enabled(source: str, enabled: bool) -> None:
    if type(enabled) is not bool:
        raise AsusctlError('Estado de alternância automática inválido.')
    _property(source, enabled)
    if _property(source) != enabled:
        raise AsusctlError('O asusd não confirmou a alternância automática.')
