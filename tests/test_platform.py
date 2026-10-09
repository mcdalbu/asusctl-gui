"""Regression coverage for disabled or unsupported automatic profiles."""
import unittest
from unittest.mock import patch
from asusctl_gui.backend import platform
from asusctl_gui.backend.asusctl import AsusctlError


class AutomaticProfileTests(unittest.TestCase):
    def test_disabled_and_enabled_are_reported_separately(self):
        with patch.object(platform, '_property', side_effect=[False, True]):
            self.assertEqual(platform.get_auto_profiles_enabled(),
                             {'ac_enabled': False, 'battery_enabled': True})

    def test_unavailable_property_does_not_claim_disabled_or_enabled(self):
        with patch.object(platform, '_property', side_effect=AsusctlError('unavailable')):
            self.assertEqual(platform.get_auto_profiles_enabled(),
                             {'ac_enabled': None, 'battery_enabled': None})

    def test_ignored_automatic_toggle_is_failure(self):
        with patch.object(platform, '_property', side_effect=[None, False]):
            with self.assertRaisesRegex(AsusctlError, 'não confirmou'):
                platform.set_auto_profile_enabled('ac', True)

    def test_non_boolean_state_is_rejected_without_write(self):
        with patch.object(platform, '_property') as prop:
            with self.assertRaises(AsusctlError):
                platform.set_auto_profile_enabled('battery', 'true')
            prop.assert_not_called()


if __name__ == '__main__':
    unittest.main()
