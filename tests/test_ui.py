"""Opt-in GTK tests with mocked hardware, run inside a graphical session."""
import os
import time
import unittest
from unittest.mock import patch

ENABLED = os.environ.get('ASUSCTL_GUI_TEST_DISPLAY') == '1'
if ENABLED:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Adw, Gtk, GLib
    from asusctl_gui.backend import asusctl, platform
    from asusctl_gui.pages.battery_page import BatteryPage
    from asusctl_gui.pages.profile_page import ProfilePage


@unittest.skipUnless(ENABLED, 'Set ASUSCTL_GUI_TEST_DISPLAY=1 in a graphical session')
class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Gtk.init_check():
            raise unittest.SkipTest('No GTK display')
        Adw.init()

    def setUp(self):
        patcher = patch.object(platform, "get_auto_profiles_enabled", return_value={"ac_enabled": False, "battery_enabled": False})
        patcher.start()
        self.addCleanup(patcher.stop)

    def wait_page(self, page):
        context = GLib.MainContext.default()
        deadline = time.monotonic() + 3
        while page._busy and time.monotonic() < deadline:
            context.iteration(False)
            time.sleep(0.005)
        self.assertFalse(page._busy, 'Operation timed out')

    def battery(self, limit=80):
        with patch.object(BatteryPage, '_fetch', return_value=(limit, {'capacity': 70, 'status': 'Discharging'})):
            page = BatteryPage()
            self.wait_page(page)
        self.addCleanup(page.dispose)
        return page

    def test_initial_loading_and_slider_selection_do_not_write(self):
        with patch.object(asusctl, 'set_battery_limit') as write:
            page = self.battery()
            self.assertEqual(page._limit.get_label(), '80%')
            page._slider.set_value(60)
            self.assertEqual(page._limit.get_label(), '80%')
            write.assert_not_called()

    def test_explicit_apply_writes_and_confirms_readback(self):
        page = self.battery()
        page._slider.set_value(60)
        with patch.object(asusctl, 'set_battery_limit') as write, \
                patch.object(page, '_fetch', return_value=(60, {'capacity': 70, 'status': 'Discharging'})):
            page._on_apply(None)
            self.wait_page(page)
            write.assert_called_once_with(60)
        self.assertEqual(page._limit.get_label(), '60%')
        self.assertFalse(page._error_group.get_visible())

    def test_failed_write_preserves_applied_value_and_shows_error(self):
        page = self.battery()
        page._slider.set_value(60)
        with patch.object(asusctl, 'set_battery_limit', side_effect=asusctl.AsusctlError('permission denied')):
            page._on_apply(None)
            self.wait_page(page)
        self.assertEqual(page._limit.get_label(), '80%')
        self.assertTrue(page._error_group.get_visible())
        self.assertEqual(page._error.get_subtitle(), 'permission denied')
        self.assertTrue(page._apply_button.get_sensitive())

    def test_ignored_write_is_not_reported_as_success(self):
        page = self.battery()
        page._slider.set_value(60)
        with patch.object(asusctl, 'set_battery_limit'), \
                patch.object(page, '_fetch', return_value=(80, {'capacity': 70, 'status': 'Discharging'})):
            page._on_apply(None)
            self.wait_page(page)
        self.assertEqual(page._limit.get_label(), '80%')
        self.assertTrue(page._error_group.get_visible())
        self.assertIn('não confirmou', page._error.get_subtitle())

    def test_initial_failure_disables_writes_and_retry_recovers(self):
        with patch.object(BatteryPage, '_fetch', side_effect=asusctl.AsusctlError('offline')):
            page = BatteryPage()
            self.wait_page(page)
        self.addCleanup(page.dispose)
        self.assertEqual(page._limit.get_label(), '—')
        self.assertFalse(page._apply_button.get_sensitive())
        self.assertTrue(page._refresh.get_sensitive())
        with patch.object(page, '_fetch', return_value=(80, {'capacity': None, 'status': ''})):
            page.refresh()
            self.wait_page(page)
        self.assertEqual(page._limit.get_label(), '80%')
        self.assertTrue(page._apply_button.get_sensitive())
        self.assertFalse(page._error_group.get_visible())

    def test_save_automatic_profile_sets_both_profile_and_enable_state(self):
        data = {'available': ['Quiet', 'Balanced'], 'active': 'Balanced', 'ac': 'Balanced', 'battery': 'Balanced'}
        flags = {'ac_enabled': False, 'battery_enabled': False}
        def set_profile(profile, source):
            data[source] = profile
        def set_enabled(source, enabled):
            flags[f'{source}_enabled'] = enabled
        with patch.object(asusctl, 'get_profiles', side_effect=lambda: dict(data)), \
                patch.object(platform, 'get_auto_profiles_enabled', side_effect=lambda: dict(flags)), \
                patch.object(asusctl, 'set_profile', side_effect=set_profile) as write, \
                patch.object(platform, 'set_auto_profile_enabled', side_effect=set_enabled) as enable:
            page = ProfilePage()
            self.wait_page(page)
            self.addCleanup(page.dispose)
            page._combos['ac'].set_selected(0)
            page._switches['ac'].set_active(True)
            write.assert_not_called()
            enable.assert_not_called()
            page._auto_buttons['ac'].emit('clicked')
            self.wait_page(page)
            self.assertFalse(page._error_group.get_visible())
            self.assertEqual(page._ac.get_label(), 'Silencioso (ativado)')
            self.assertEqual(page._battery.get_label(), 'Equilibrado (desativado)')
            self.assertTrue(page._switches['ac'].get_active())
            write.assert_called_once_with('Quiet', 'ac')
            enable.assert_called_once_with('ac', True)

    def test_unavailable_automatic_properties_disable_save(self):
        data = {'available': ['Quiet', 'Balanced'], 'active': 'Balanced', 'ac': 'Balanced', 'battery': 'Quiet'}
        with patch.object(asusctl, 'get_profiles', return_value=data), \
                patch.object(platform, 'get_auto_profiles_enabled', return_value={'ac_enabled': None, 'battery_enabled': None}):
            page = ProfilePage()
            self.wait_page(page)
            self.addCleanup(page.dispose)
            self.assertFalse(page._auto_buttons['ac'].get_sensitive())
            self.assertFalse(page._switches['battery'].get_sensitive())
            self.assertIn('estado indisponível', page._ac.get_label())

    def test_profiles_follow_available_list_and_do_not_write_on_load(self):
        data = {'available': ['Quiet', 'Balanced'], 'active': 'Balanced', 'ac': 'Balanced', 'battery': 'Quiet'}
        with patch.object(asusctl, 'get_profiles', return_value=data), patch.object(asusctl, 'set_profile') as write:
            page = ProfilePage()
            self.wait_page(page)
            self.addCleanup(page.dispose)
            self.assertFalse(page._buttons['Performance'].get_sensitive())
            self.assertFalse(page._buttons['Balanced'].get_sensitive())
            self.assertTrue(page._buttons['Quiet'].get_sensitive())
            self.assertEqual(page._combos['battery'].get_selected(), 0)
            self.assertFalse(page._switches["ac"].get_active())
            self.assertIn("desativado", page._ac.get_label())
            write.assert_not_called()


if __name__ == '__main__':
    unittest.main()
