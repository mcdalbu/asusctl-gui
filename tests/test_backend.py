"""Protocol/error regression tests; no calls to real hardware."""
import subprocess
import unittest
from unittest.mock import patch
from asusctl_gui.backend import asusctl
from asusctl_gui.backend import keyboard

INFO = '''asusctl v6.3.8
Software version: 6.3.8
Product family: ASUS Vivobook S 14
Board name: S5406SA
Supported Core Functions:
[
    "xyz.ljones.Platform",
    "xyz.ljones.Backlight",
]
Supported Platform Properties:
[
    ChargeControlEndThreshold,
    ThrottlePolicy,
]
No aura interface found
'''


class CliTests(unittest.TestCase):
    def result(self, code=0, out='', err=''):
        return subprocess.CompletedProcess(['asusctl'], code, out, err)

    def test_nonzero_without_error_keyword_fails(self):
        with patch.object(asusctl.subprocess, 'run', return_value=self.result(1, '', 'permission denied')):
            with self.assertRaisesRegex(asusctl.AsusctlError, 'permission denied'):
                asusctl.set_profile('Balanced')

    def test_success_exit_missing_aura_is_failure(self):
        with patch.object(asusctl.subprocess, 'run', return_value=self.result(out='No aura interface found')):
            with self.assertRaises(asusctl.AsusctlError):
                asusctl._run('leds', 'get')

    def test_success_exit_error_is_failure(self):
        with patch.object(asusctl.subprocess, 'run', return_value=self.result(out='Error: D-Bus unavailable')):
            with self.assertRaises(asusctl.AsusctlError):
                asusctl.get_battery_limit()

    def test_missing_executable(self):
        with patch.object(asusctl.subprocess, 'run', side_effect=FileNotFoundError):
            with self.assertRaisesRegex(asusctl.AsusctlError, 'não encontrado'):
                asusctl.get_profiles()

    def test_timeout(self):
        with patch.object(asusctl.subprocess, 'run', side_effect=subprocess.TimeoutExpired('asusctl', 10)):
            with self.assertRaisesRegex(asusctl.AsusctlError, 'demorou'):
                asusctl.get_profiles()

    def test_log_filter_keeps_actual_values(self):
        with patch.object(asusctl.subprocess, 'run', return_value=self.result(
                out='[INFO zbus] handshaking\nCurrent battery charge limit: 80%')):
            self.assertEqual(asusctl.get_battery_limit(), 80)

    def test_battery_read_failure_does_not_invent_full_charge(self):
        for out in ('', 'Battery: 80%', 'Current battery charge limit: 101%'):
            with self.subTest(out=out), patch.object(asusctl, '_run', return_value=out):
                with self.assertRaises(asusctl.AsusctlError):
                    asusctl.get_battery_limit()

    def test_battery_rejects_invalid_limits_without_call(self):
        with patch.object(asusctl, '_run') as run:
            for value in (19, 101, True, 80.9, '80'):
                with self.subTest(value=value), self.assertRaises(asusctl.AsusctlError):
                    asusctl.set_battery_limit(value)
            run.assert_not_called()

    def test_profile_get_and_automatic_profiles(self):
        with patch.object(asusctl, '_run', side_effect=[
                'Quiet\nBalanced\nPerformance',
                'Active profile: Balanced\n\nAC profile Performance\nBattery profile Quiet']):
            data = asusctl.get_profiles()
        self.assertEqual(data['active'], 'Balanced')
        self.assertEqual(data['ac'], 'Performance')
        self.assertEqual(data['battery'], 'Quiet')

    def test_profile_failure_does_not_invent_balanced(self):
        with patch.object(asusctl, '_run', side_effect=['Quiet\nBalanced', '']):
            with self.assertRaises(asusctl.AsusctlError):
                asusctl.get_profiles()

    def test_invalid_profile_is_not_sent(self):
        with patch.object(asusctl, '_run') as run:
            with self.assertRaises(asusctl.AsusctlError):
                asusctl.set_profile('Turbo')
            with self.assertRaises(asusctl.AsusctlError):
                asusctl.set_profile('Balanced', '--evil')
            run.assert_not_called()

    def test_automatic_profile_uses_source_flag(self):
        with patch.object(asusctl, '_run') as run:
            asusctl.set_profile('Quiet', 'battery')
            run.assert_called_once_with('profile', 'set', '--battery', 'Quiet')

    def test_vivobook_detection_is_read_only_and_does_not_assume_screenpad_aura(self):
        with patch.object(asusctl.subprocess, 'run', return_value=self.result(out=INFO)) as run, \
                patch.object(keyboard, 'get_brightness', return_value=(0, 3)):
            info = asusctl.get_system_info()
        self.assertTrue(info.daemon_available)
        self.assertTrue(info.has_profiles)
        self.assertTrue(info.has_battery_limit)
        self.assertTrue(info.has_keyboard)
        self.assertFalse(info.has_aura)
        self.assertFalse(info.has_fan_curves)
        self.assertFalse(info.has_armoury)
        self.assertEqual(info.asusctl_version, '6.3.8')
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], ['asusctl', 'info', '--show-supported'])

    def test_keyboard_remains_available_when_asusd_fails(self):
        with patch.object(asusctl, '_run', side_effect=asusctl.AsusctlError('offline')), \
                patch.object(keyboard, 'get_brightness', return_value=(1, 3)):
            info = asusctl.get_system_info()
        self.assertTrue(info.has_keyboard)
        self.assertFalse(info.has_profiles)
        self.assertFalse(info.has_battery_limit)
        self.assertFalse(info.daemon_available)
        self.assertEqual(info.error, 'offline')

    def test_keyboard_maximum_is_not_assumed(self):
        with patch.object(keyboard, '_call', side_effect=[(2,), (1,)]):
            self.assertEqual(keyboard.get_brightness(), (1, 2))
        with patch.object(keyboard, '_call', return_value=(2,)) as call:
            with self.assertRaises(asusctl.AsusctlError):
                keyboard.set_brightness(3)
            call.assert_called_once_with('GetMaxBrightness')


if __name__ == '__main__':
    unittest.main()
