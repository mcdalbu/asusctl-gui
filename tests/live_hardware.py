"""Opt-in end-to-end GTK test with real hardware and guaranteed restore attempts.

Run only with --allow-hardware-changes inside a graphical session. This script
briefly changes profiles, charge thresholds and keyboard lighting. It saves
original values before any write and restores them in finally, even on failure.
It does not unplug AC, discharge the battery or restart system services.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def wait(predicate, timeout=30):
    from gi.repository import GLib
    context = GLib.MainContext.default()
    end = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > end:
            raise TimeoutError('A operação GTK não terminou dentro do prazo.')
        # Drain pending GTK frame events so lower-priority idle callbacks run.
        for _ in range(100):
            if not context.pending():
                break
            context.iteration(False)
        time.sleep(0.001)


def config_values():
    path = Path('/etc/asusd/asusd.ron')
    if not path.exists():
        return {}
    import re
    return dict(re.findall(r'^\s*((?:base_)?charge_control_end_threshold|change_platform_profile_on_(?:ac|battery)|platform_profile_on_(?:ac|battery)):\s*([^,]+),', path.read_text(), re.M))


def epp_values():
    return {str(path): path.read_text().strip() for path in Path('/sys/devices/system/cpu/cpufreq').glob('policy*/energy_performance_preference')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-hardware-changes', action='store_true')
    parser.add_argument('--report', type=Path, default=ROOT / 'build/validation-live.json')
    args = parser.parse_args()
    if not args.allow_hardware_changes:
        parser.error('Hardware writes require explicit --allow-hardware-changes')
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Adw, Gtk
    from asusctl_gui.backend import asusctl, keyboard, platform
    from asusctl_gui.pages.profile_page import display
    from asusctl_gui.window import MainWindow
    if not Gtk.init_check():
        raise RuntimeError('Sessão gráfica GTK indisponível.')
    Adw.init()
    original = {'profiles': asusctl.get_profiles(), 'auto': platform.get_auto_profiles_enabled(),
                'limit': asusctl.get_battery_limit(), 'keyboard': keyboard.get_brightness()[0],
                'config': config_values(), 'epp': epp_values()}
    if original['config'].get('base_charge_control_end_threshold', str(original['limit'])) != str(original['limit']):
        raise RuntimeError('Há uma carga temporária prévia ativa. Conclua ou cancele antes deste teste.')
    if any(v is None for v in original['auto'].values()):
        raise RuntimeError('Não é possível salvar o estado original da alternância automática.')
    results = {'date': datetime.now(ZoneInfo('America/Fortaleza')).isoformat(),
               'device': asusctl.get_system_info().product_name, 'original': original,
               'checks': [], 'restore_errors': [], 'limitations': [
                   'Sem desconexão física de AC: evento de troca da fonte de energia não testado.',
                   'Carga temporária: ativação e limite verificados; ciclo completo de recarga não executado.']}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    window = None

    def record(name, action):
        try:
            detail = action()
        except Exception as exc:
            results['checks'].append({'name': name, 'status': 'FAIL', 'detail': str(exc)})
            print('FAIL:', name, str(exc), flush=True)
            raise
        results['checks'].append({'name': name, 'status': 'PASS', 'detail': detail})
        print('PASS:', name, detail, flush=True)

    def completed(page):
        wait(lambda: not page._busy)
        if page._error_group.get_visible():
            raise RuntimeError(page._error.get_subtitle())

    try:
        window = MainWindow()
        window.present()
        wait(lambda: not window._probing and all(not page._busy for page in window._pages.values()))
        assert set(window._pages) == {'profile', 'battery', 'keyboard', 'info'}
        profile, battery, keys = (window._pages[name] for name in ('profile', 'battery', 'keyboard'))
        for page in (profile, battery, keys):
            completed(page)
        record('Detecção e carregamento GTK', lambda: list(window._pages))

        for name in original['profiles']['available']:
            def change(name=name):
                profile._buttons[name].emit('clicked')
                completed(profile)
                data = asusctl.get_profiles()
                kernel = Path('/sys/firmware/acpi/platform_profile').read_text().strip()
                assert data['active'] == name, data
                assert kernel == name.lower(), kernel
                assert profile._active.get_label() == display(name)
                return {'daemon': data['active'], 'kernel': kernel, 'gui': profile._active.get_label()}
            record(f'Perfil {name}', change)

        for source in ('ac', 'battery'):
            for enabled in (True, False):
                target = 'Quiet' if enabled else 'Balanced'
                def automatic(source=source, enabled=enabled, target=target):
                    profile._combos[source].set_selected(profile._available.index(target))
                    profile._switches[source].set_active(enabled)
                    profile._auto_buttons[source].emit('clicked')
                    completed(profile)
                    data = asusctl.get_profiles()
                    flags = platform.get_auto_profiles_enabled()
                    assert data[source] == target, data
                    assert flags[f'{source}_enabled'] == enabled, flags
                    config = config_values()
                    key = 'ac' if source == 'ac' else 'battery'
                    assert config[f'platform_profile_on_{key}'] == target, config
                    assert config[f'change_platform_profile_on_{key}'] == str(enabled).lower(), config
                    return {'profile': target, 'enabled': enabled, 'persisted': True}
                record(f'Perfil automático {source}: {enabled}', automatic)

        for value in (20, 60, 80, 55, 100):
            def limit(value=value):
                before = asusctl.get_battery_limit()
                battery._slider.set_value(value)
                assert asusctl.get_battery_limit() == before, 'Slider gravou sem Aplicar'
                battery._apply_button.emit('clicked')
                completed(battery)
                daemon = asusctl.get_battery_limit()
                kernel = int(Path('/sys/class/power_supply/BAT0/charge_control_end_threshold').read_text())
                assert daemon == value and kernel == value, (daemon, kernel)
                assert battery._limit.get_label() == f'{value}%'
                return {'daemon': daemon, 'kernel': kernel, 'gui': battery._limit.get_label()}
            record(f'Limite de carga {value}%', limit)

        for value in range(keys._maximum + 1):
            def brightness(value=value):
                before = keyboard.get_brightness()[0]
                keys._slider.set_value(value)
                assert keyboard.get_brightness()[0] == before, 'Slider gravou sem Aplicar'
                keys._button.emit('clicked')
                completed(keys)
                daemon = keyboard.get_brightness()[0]
                kernel = int(Path('/sys/class/leds/asus::kbd_backlight/brightness').read_text())
                assert daemon == value and kernel == value, (daemon, kernel)
                assert keys._current.get_label() == f'{value} / {keys._maximum}'
                return {'upower': daemon, 'kernel': kernel, 'gui': keys._current.get_label()}
            record(f'Brilho do teclado {value}', brightness)

        def oneshot():
            battery._slider.set_value(80)
            battery._apply_button.emit('clicked')
            completed(battery)
            battery._oneshot(None)
            completed(battery)
            config = config_values()
            kernel = int(Path('/sys/class/power_supply/BAT0/charge_control_end_threshold').read_text())
            assert kernel == 100, kernel
            assert config['base_charge_control_end_threshold'] == '80', config
            return {'temporary_threshold': kernel, 'saved_base': config['base_charge_control_end_threshold']}
        record('Carga completa temporária: ativação', oneshot)

        def refresh():
            for page in (profile, battery, keys):
                page._refresh.emit('clicked')
                completed(page)
            for i in range(4):
                window._nav.select_row(window._nav.get_row_at_index(i))
            window._refresh.emit('clicked')
            wait(lambda: not window._probing and all(not p._busy for p in window._pages.values()))
            assert set(window._pages) == {'profile', 'battery', 'keyboard', 'info'}
            return 'Leitura atualizada, navegação e nova detecção concluídas'
        record('Atualização e navegação', refresh)
    finally:
        # Attempt every restore independently, including after a failed check.
        restores = [(f'auto {s}', lambda s=s: platform.set_auto_profile_enabled(s, original['auto'][f'{s}_enabled'])) for s in ('ac', 'battery')]
        restores += [(f'perfil {s}', lambda s=s: asusctl.set_profile(original['profiles'][s], s)) for s in ('ac', 'battery')]
        restores += [('perfil ativo', lambda: asusctl.set_profile(original['profiles']['active'])),
                     ('bateria', lambda: asusctl.set_battery_limit(original['limit'])),
                     ('teclado', lambda: keyboard.set_brightness(original['keyboard']))]
        for name, restore in restores:
            try:
                restore()
            except Exception as exc:
                results['restore_errors'].append(f'{name}: {exc}')
        try:
            final = {'profiles': asusctl.get_profiles(), 'auto': platform.get_auto_profiles_enabled(),
                     'limit': asusctl.get_battery_limit(), 'keyboard': keyboard.get_brightness()[0],
                     'config': config_values(), 'epp': epp_values()}
            results['final'] = final
            results['restored'] = final == original and not results['restore_errors']
        except Exception as exc:
            results['restore_errors'].append(str(exc))
            results['restored'] = False
        if window:
            window.close()
        args.report.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print('Restaurado:', results['restored'], 'Relatório:', args.report, flush=True)
    return 0 if results.get('restored') and all(c['status'] == 'PASS' for c in results['checks']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
