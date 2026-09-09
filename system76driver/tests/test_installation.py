"""Regression tests for installation failures, dry runs and Surface packages."""

from os import path
import runpy
from subprocess import CalledProcessError
from unittest import TestCase
from unittest.mock import mock_open, patch

import system76driver
from system76driver import actions
from system76driver.products import PRODUCTS


class NeededAction(actions.Action):
    update_grub = True
    update_initramfs = True

    def get_isneeded(self):
        return True

    def describe(self):
        return 'Install a test driver'

    def perform(self):
        raise AssertionError('A dry run must not perform actions')


class TestInstallation(TestCase):
    def test_dry_run_never_changes_boot_configuration(self):
        with patch.object(actions.SubProcess, 'check_call') as command:
            messages = list(actions.ActionRunner([NeededAction]).run_iter(dry=True))
        self.assertEqual(messages, ['Install a test driver'])
        command.assert_not_called()

    def test_package_failure_stops_remaining_actions(self):
        with patch.object(actions.SubProcess, 'check_call',
                          side_effect=CalledProcessError(100, ['apt-get'])) as command:
            runner = actions.ActionRunner([
                actions.rgb_keyboard_driver, actions.linux_controlcenter_app,
            ])
            with self.assertRaises(CalledProcessError):
                list(runner.run_iter())
        self.assertEqual(command.call_count, 1)

    def test_bundled_packages_are_found_outside_the_checkout(self):
        with patch.object(actions.SubProcess, 'check_call') as command:
            actions.yt6801_driver().perform()
        filename = command.call_args.args[0][-1]
        self.assertTrue(path.isabs(filename))
        self.assertTrue(path.isfile(filename))

    def test_cli_path_and_privilege_escalation(self):
        for uid, prefix in [(0, []), (1000, ['pkexec'])]:
            with self.subTest(uid=uid), patch('sys.argv', ['/opt/LUD source/system76-driver']), \
                    patch('os.getuid', return_value=uid):
                self.assertEqual(system76driver.get_cli_command(),
                                 prefix + ['/opt/LUD source/system76-driver-cli'])


class TestCLI(TestCase):
    def run_cli(self, arguments, model='fox1', uid=0):
        script = path.join(path.dirname(path.dirname(path.dirname(__file__))),
                           'system76-driver-cli')
        with patch('sys.argv', [script] + arguments), \
                patch('os.getuid', return_value=uid), \
                patch('os.path.exists', return_value=False), \
                patch('system76driver.model.determine_model_new', return_value=model), \
                patch('system76driver.actions.ActionRunner') as runner:
            runner.return_value.run_iter.return_value = iter(['Install a driver'])
            runpy.run_path(script, run_name='__main__')
            return runner

    def test_cli_detects_ekimia_and_preserves_dry_run(self):
        runner = self.run_cli(['--dry', '--strict'])
        runner.assert_called_once_with(PRODUCTS['fox1']['drivers'])
        runner.return_value.run_iter.assert_called_once_with(dry=True)

    def test_unknown_model_stops_before_installation(self):
        with self.assertRaises(SystemExit) as error:
            self.run_cli(['--strict'], model='unknown-model')
        self.assertEqual(error.exception.code, 2)

    def test_non_root_is_an_error_even_without_strict(self):
        with self.assertRaises(SystemExit) as error:
            self.run_cli([], uid=1000)
        self.assertEqual(error.exception.code, 1)

    def test_execution_failure_is_not_reported_as_success(self):
        with patch('system76driver.actions.ActionRunner.run_iter',
                   side_effect=CalledProcessError(100, ['apt-get'])):
            script = path.join(path.dirname(path.dirname(path.dirname(__file__))),
                               'system76-driver-cli')
            with patch('sys.argv', [script, '--model', 'rebel1']), \
                    patch('os.getuid', return_value=0), \
                    patch('os.path.exists', return_value=False), \
                    self.assertRaises(SystemExit) as error:
                runpy.run_path(script, run_name='__main__')
        self.assertEqual(error.exception.code, 1)


class TestSurfaceInstallation(TestCase):
    def test_repository_refresh_packages_and_secure_boot(self):
        releases = [
            ('ubuntu', '24', 'noble', True),
            ('ubuntu', '26', 'resolute', False),
            ('debian', '13', 'trixie', True),
            ('debian', '', 'sid', False),
            ('debian', '14', 'forky', False),
        ]
        for distribution, major, codename, wacom in releases:
            with self.subTest(distribution=distribution, codename=codename), \
                    patch.object(actions.distro, 'id', return_value=distribution), \
                    patch.object(actions.distro, 'major_version', return_value=major), \
                    patch.object(actions.distro, 'codename', return_value=codename), \
                    patch.object(actions.SubProcess, 'check_output', return_value=b'key'), \
                    patch.object(actions.SubProcess, 'check_call') as command, \
                    patch.object(actions, 'atomic_write'), \
                    patch('builtins.open', mock_open()):
                actions.enablesurfacekernel().perform()
            calls = [item.args[0] for item in command.call_args_list]
            self.assertEqual(calls[0], ['apt-get', 'update'])
            self.assertEqual('libwacom-surface' in calls[1], wacom)
            self.assertIn('--no-remove', calls[1])
            self.assertIn('linux-image-surface', calls[1])
            self.assertIn('linux-surface-secureboot-mok', calls[2])

    def test_failed_key_download_does_not_modify_apt(self):
        with patch.object(actions.SubProcess, 'check_output',
                          side_effect=CalledProcessError(4, ['wget'])), \
                patch.object(actions.SubProcess, 'check_call') as command, \
                patch('builtins.open', mock_open()) as files, \
                patch.object(actions, 'atomic_write') as write:
            with self.assertRaises(CalledProcessError):
                actions.enablesurfacekernel().perform()
        command.assert_not_called()
        files.assert_not_called()
        write.assert_not_called()
