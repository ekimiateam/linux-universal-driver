# system76-driver: Universal driver for System76 computers
# Copyright (C) 2005-2016 System76, Inc.
#
# This file is part of `system76-driver`.
#
# `system76-driver` is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# `system76-driver` is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with `system76-driver`; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""
Unit tests for `system76driver.util` module.
"""

from unittest import TestCase
from unittest.mock import patch
import json
import os
from os import path
import shutil
import subprocess

from .helpers import TempDir
from system76driver.mockable import SubProcess
from system76driver import util


class TestFunctions(TestCase):
    def test_create_tmp_logs(self):
        SubProcess.reset(mocking=False)
        (tmp, tgz) = util.create_tmp_logs(func=None)
        self.assertTrue(path.isdir(tmp))
        self.assertTrue(tmp.startswith('/tmp/logs.'))
        self.assertEqual(
            sorted(os.listdir(tmp)),
            ['lud-logs', 'lud-logs.tgz'],
        )
        self.assertEqual(tgz, path.join(tmp, 'lud-logs.tgz'))
        self.assertTrue(path.isfile(tgz))
        base = path.join(tmp, 'lud-logs')
        self.assertTrue(path.isdir(base))
        self.assertIn('metadata.json', os.listdir(base))
        with open(path.join(base, 'metadata.json')) as fp:
            metadata = json.load(fp)
        self.assertIs(metadata['redacted'], True)
        shutil.rmtree(tmp)

    def test_create_logs(self):
        SubProcess.reset(mocking=False)
        tmp = TempDir()
        tgz = util.create_logs(tmp.dir, func=None)
        self.assertEqual(tgz, tmp.join('lud-logs.tgz'))
        self.assertTrue(path.isfile(tgz))


class TestRedactText(TestCase):
    def test_dmi_serial_line(self):
        data = b'System Information\nSerial Number: ABC123XYZ\nManufacturer: Ekimia\n'
        result = util.redact_text(data)
        self.assertNotIn(b'ABC123XYZ', result)
        self.assertIn(b'Serial Number: <redacted>', result)

    def test_dmi_uuid_line(self):
        data = b'UUID: 4c4c4544-0034-3510-8052-c7c04f503432\n'
        result = util.redact_text(data)
        self.assertNotIn(b'4c4c4544-0034-3510-8052-c7c04f503432', result)
        self.assertIn(b'UUID: <redacted>', result)

    def test_generic_uuid(self):
        data = b'Filesystem UUID=1b4e28ba-2fa1-11d2-883f-0016d3cca427 mounted\n'
        result = util.redact_text(data)
        self.assertNotIn(b'1b4e28ba-2fa1-11d2-883f-0016d3cca427', result)
        self.assertIn(b'<uuid>', result)

    def test_fstab_partuuid_short_form(self):
        # MBR-style PARTUUID (e.g. from /etc/fstab) isn't a full UUID and
        # would otherwise pass the generic UUID pattern untouched.
        data = b'PARTUUID=9e1e7f3c-01 /boot vfat defaults 0 2\n'
        result = util.redact_text(data)
        self.assertNotIn(b'9e1e7f3c-01', result)
        self.assertIn(b'PARTUUID=<uuid>', result)

    def test_bare_serial_label(self):
        data = b'serial: ABCD123456\n'
        result = util.redact_text(data)
        self.assertNotIn(b'ABCD123456', result)
        self.assertIn(b'serial: <redacted>', result)

    def test_lsusb_iserial_descriptor_line(self):
        data = b'iSerial                 3 ABCD123456\n'
        result = util.redact_text(data)
        self.assertNotIn(b'ABCD123456', result)
        self.assertIn(b'iSerial                 3 <redacted>', result)

    def test_lspci_device_serial_number_capability(self):
        data = b'Device Serial Number 00-11-22-33-44-55-66-77\n'
        result = util.redact_text(data)
        self.assertNotIn(b'00-11-22-33-44-55-66-77', result)
        self.assertIn(b'Device Serial Number <redacted>', result)

    def test_serial_number_prose_kept(self):
        data = b'the serial number was reset after the update\n'
        self.assertEqual(util.redact_text(data), data)

    def test_mac_address(self):
        data = b'eth0: link encap:Ethernet HWaddr 00:1A:2B:3C:4D:5E\n'
        result = util.redact_text(data)
        self.assertNotIn(b'00:1A:2B:3C:4D:5E', result)
        self.assertIn(b'<mac>', result)

    def test_ipv4_address(self):
        data = b'inet 192.168.1.42 netmask 255.255.255.0\n'
        result = util.redact_text(data)
        self.assertNotIn(b'192.168.1.42', result)
        self.assertIn(b'<ip>', result)

    def test_loopback_ipv4_kept(self):
        data = b'inet 127.0.0.1 netmask 255.0.0.0\n'
        result = util.redact_text(data)
        self.assertIn(b'127.0.0.1', result)

    def test_ipv6_address(self):
        data = b'inet6 fe80:0:0:0:216:3eff:fe74:3d3e/64\n'
        result = util.redact_text(data)
        self.assertNotIn(b'fe80:0:0:0:216:3eff:fe74:3d3e', result)
        self.assertIn(b'<ip>', result)

    def test_ipv6_regex_leaves_syslog_timestamp_alone(self):
        data = b'Sep 12 10:23:45 box kernel: usb 1-1: new device\n'
        self.assertEqual(util.redact_text(data), data)

    def test_ipv6_regex_leaves_pci_address_alone(self):
        data = b'0000:00:02.0 VGA compatible controller\n'
        self.assertEqual(util.redact_text(data), data)

    def test_home_path(self):
        data = b'/home/alice/.config/foo.conf: No such file or directory\n'
        result = util.redact_text(data)
        self.assertNotIn(b'alice', result)
        self.assertIn(b'/home/<user>/.config/foo.conf', result)

    def test_home_path_without_trailing_slash(self):
        data = b'/home/alice\n'
        result = util.redact_text(data)
        self.assertNotIn(b'alice', result)
        self.assertIn(b'/home/<user>', result)

    def test_hostname(self):
        import socket
        hostname = socket.gethostname()
        data = ('journal on ' + hostname + ' rotated\n').encode()
        result = util.redact_text(data)
        self.assertNotIn(hostname.encode(), result)
        self.assertIn(b'<hostname>', result)

    def test_wifi_ssid_in_connection_activation(self):
        data = b"device (wlp2s0): Activation: (wifi) connection 'Home-WiFi' enable...\n"
        result = util.redact_text(data)
        self.assertNotIn(b'Home-WiFi', result)
        self.assertIn(b"'<ssid>'", result)

    def test_wifi_ssid_in_config_added_value(self):
        data = b"Config: added 'ssid' value 'Home-WiFi' (9 bytes)\n"
        result = util.redact_text(data)
        self.assertNotIn(b'Home-WiFi', result)

    def test_unquoted_ssid_label(self):
        data = b'SSID: HomeNetwork\n'
        result = util.redact_text(data)
        self.assertNotIn(b'HomeNetwork', result)
        self.assertIn(b'SSID: <ssid>', result)

    def test_apt_history_requested_by(self):
        data = b'Requested-By: alice (1000)\n'
        result = util.redact_text(data)
        self.assertNotIn(b'alice', result)
        self.assertIn(b'Requested-By: <redacted>', result)

    def test_apt_source_url_credentials(self):
        data = b'deb https://alice:s3cret@example.com/repo stable main\n'
        result = util.redact_text(data)
        self.assertNotIn(b'alice:s3cret', result)
        self.assertIn(b'https://<redacted>@example.com/repo stable main', result)

    def test_authorization_header(self):
        data = b'Authorization: Bearer abc.def.ghi\n'
        result = util.redact_text(data)
        self.assertNotIn(b'abc.def.ghi', result)
        self.assertIn(b'Authorization: <redacted>', result)

    def test_unrelated_quoted_line_kept(self):
        data = b"apt-get: Unable to fetch some archives, maybe run 'apt-get update'\n"
        self.assertEqual(util.redact_text(data), data)

    def test_credential_line(self):
        data = b'DB_PASSWORD=hunter2\nAuthorization token: abc.def.ghi\n'
        result = util.redact_text(data)
        self.assertNotIn(b'hunter2', result)
        self.assertNotIn(b'abc.def.ghi', result)

    def test_unmatched_text_unchanged(self):
        data = b'nothing sensitive here, just a normal log line\n'
        self.assertEqual(util.redact_text(data), data)


class TestRedactLogs(TestCase):
    def test_redacts_file_content(self):
        tmp = TempDir()
        tmp.write(b'Serial Number: SECRET123\n', 'dmidecode')
        util.redact_logs(tmp.dir)
        with open(tmp.join('dmidecode'), 'rb') as fp:
            content = fp.read()
        self.assertNotIn(b'SECRET123', content)
        self.assertIn(b'<redacted>', content)

    def test_recurses_into_subdirectories(self):
        tmp = TempDir()
        tmp.makedirs('apt')
        tmp.write(b'deb http://192.168.1.5/mirror focal main\n', 'apt', 'sources.list')
        util.redact_logs(tmp.dir)
        with open(tmp.join('apt', 'sources.list'), 'rb') as fp:
            content = fp.read()
        self.assertNotIn(b'192.168.1.5', content)

    def test_removes_gz_files_instead_of_leaving_them_unredacted(self):
        # dump_logs() no longer collects any .gz files by default (see
        # TestDumpLogs), but if one shows up anyway, redact_logs() can't
        # safely rewrite a compressed file as text - fail closed and
        # drop it from the bundle rather than ship it unredacted.
        tmp = TempDir()
        tmp.makedirs('some')
        tmp.write(b'Serial Number: SECRET123\n', 'some', 'file.gz')
        excluded = util.redact_logs(tmp.dir)
        self.assertFalse(path.exists(tmp.join('some', 'file.gz')))
        self.assertEqual(excluded, [path.join('some', 'file.gz')])

    def test_leaves_unmatched_files_unchanged(self):
        tmp = TempDir()
        original = b'nothing sensitive here\n'
        tmp.write(original, 'uptime')
        util.redact_logs(tmp.dir)
        with open(tmp.join('uptime'), 'rb') as fp:
            content = fp.read()
        self.assertEqual(content, original)


class TestDumpJournal(TestCase):
    def test_runs_five_scoped_invocations(self):
        tmp = TempDir()
        with patch('system76driver.util.subprocess.run') as run:
            run.return_value.stdout = ''
            run.return_value.stderr = ''
            util.dump_journal(tmp.dir)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands, [
            'journalctl -k --since yesterday',
            'journalctl -u NetworkManager --since yesterday',
            'journalctl -u systemd-suspend --since yesterday',
            'journalctl -t dkms --since yesterday',
            'journalctl -t system76-daemon --since yesterday',
        ])

    def test_writes_one_file_per_invocation(self):
        tmp = TempDir()
        with patch('system76driver.util.subprocess.run') as run:
            run.return_value.stdout = ''
            run.return_value.stderr = ''
            util.dump_journal(tmp.dir)
        self.assertEqual(sorted(os.listdir(tmp.dir)), [
            'journalctl-NetworkManager',
            'journalctl-dkms',
            'journalctl-kernel',
            'journalctl-system76-daemon',
            'journalctl-systemd-suspend',
        ])


class TestWriteMetadata(TestCase):
    def test_writes_expected_keys(self):
        tmp = TempDir()
        tmp.write(b'dummy', 'dmesg')
        util.write_metadata(tmp.dir)
        with open(tmp.join('metadata.json')) as fp:
            metadata = json.load(fp)
        self.assertEqual(metadata['format_version'], 1)
        self.assertIs(metadata['redacted'], True)
        self.assertIn('dmesg', metadata['collectors'])
        self.assertEqual(metadata['excluded_files'], [])
        self.assertEqual(
            set(metadata['excluded_categories']),
            {'serial_numbers', 'uuids', 'mac_addresses', 'hostname',
             'home_paths', 'ip_addresses', 'credentials', 'wifi_ssids',
             'user_identity'},
        )

    def test_excluded_files_names_any_removed_file(self):
        tmp = TempDir()
        util.write_metadata(tmp.dir, excluded_files=['some/file.gz'])
        with open(tmp.join('metadata.json')) as fp:
            metadata = json.load(fp)
        self.assertEqual(metadata['excluded_files'], ['some/file.gz'])


class TestCreateTmpLogsEndToEnd(TestCase):
    def test_full_pipeline_leaves_no_sensitive_value_in_the_tar(self):
        import socket
        hostname = socket.gethostname() or 'testhostname'

        sensitive = {
            'dmi serial': 'ABCD1234SERIAL',
            'system uuid': '4c4c4544-0034-3510-8052-c7c04f503432',
            'filesystem uuid': '1b4e28ba-2fa1-11d2-883f-0016d3cca427',
            'partuuid': '9e1e7f3c-01',
            'usb serial': 'USBSERIAL42',
            'pci serial': '00-11-22-33-44-55-66-77',
            'mac': '00:1A:2B:3C:4D:5E',
            'username': 'alice',
            'ipv4': '192.168.1.42',
            'ipv6': 'fe80:0:0:0:216:3eff:fe74:3d3e',
            'ssid': 'Home-WiFi-Network',
            'unquoted ssid': 'HomeNetwork',
            'credential': 'hunter2super',
            'repo credential': 's3cret',
            'auth token': 'abc.def.ghi',
        }

        def fake_dump(base):
            with open(path.join(base, 'dmidecode'), 'w') as fp:
                fp.write(
                    'Serial Number: {dmi serial}\n'
                    'UUID: {system uuid}\n'.format(**sensitive)
                )
            with open(path.join(base, 'lsblk'), 'w') as fp:
                fp.write('NAME FSTYPE MOUNTPOINTS LABEL\nsda1 ext4   /            data\n')
            with open(path.join(base, 'fstab'), 'w') as fp:
                fp.write(
                    'UUID={filesystem uuid} / ext4 defaults 0 1\n'
                    'PARTUUID={partuuid} /boot vfat defaults 0 2\n'.format(**sensitive)
                )
            with open(path.join(base, 'lsusb'), 'w') as fp:
                fp.write('Bus 001 Device 003: ID 0bda:8153 Realtek\n')
            with open(path.join(base, 'lspci'), 'w') as fp:
                fp.write(
                    '00:1f.3 Audio device [0403]: Intel Corp [8086:9d71]\n'
                    'Kernel driver in use: snd_hda_intel\n'
                    'Capabilities: [178 v1] Device Serial Number {pci serial}\n'.format(**sensitive)
                )
            with open(path.join(base, 'journalctl-NetworkManager'), 'w') as fp:
                fp.write(
                    "device (wlp2s0): Activation: (wifi) connection '{ssid}' enable\n"
                    'SSID: {unquoted ssid}\n'
                    'eth0: link encap:Ethernet HWaddr {mac}\n'
                    'inet {ipv4} netmask 255.255.255.0\n'
                    'inet6 {ipv6}/64\n'.format(**sensitive)
                )
            os.makedirs(path.join(base, 'apt'))
            with open(path.join(base, 'apt', 'history'), 'w') as fp:
                fp.write(
                    '/home/{username}\n'
                    'Requested-By: {username} (1000)\n'
                    'built on {hostname}\n'
                    'DB_PASSWORD={credential}\n'
                    'Authorization: Bearer {auth token}\n'.format(hostname=hostname, **sensitive)
                )
            with open(path.join(base, 'apt', 'sources.list'), 'w') as fp:
                fp.write(
                    'deb https://{username}:{repo credential}@example.com/repo stable main\n'
                    .format(**sensitive)
                )

        SubProcess.reset(mocking=False)
        (tmp, tgz) = util.create_tmp_logs(func=fake_dump)
        extract_dir = path.join(tmp, 'extracted')
        os.mkdir(extract_dir)
        subprocess.run(['tar', '-xzf', tgz, '-C', extract_dir], check=True)
        base = path.join(extract_dir, 'lud-logs')

        tar_text = b''
        for root, _dirs, files in os.walk(base):
            for name in files:
                with open(path.join(root, name), 'rb') as fp:
                    tar_text += fp.read()

        for label, value in sensitive.items():
            self.assertNotIn(value.encode(), tar_text, 'leaked ' + label)
        self.assertNotIn(hostname.encode(), tar_text)

        for placeholder in (b'<redacted>', b'<uuid>', b'<mac>', b'<ip>', b'<ssid>', b'<hostname>'):
            self.assertIn(placeholder, tar_text)

        with open(path.join(base, 'metadata.json')) as fp:
            metadata = json.load(fp)
        self.assertIn('dmidecode', metadata['collectors'])
        self.assertEqual(metadata['excluded_files'], [])

        shutil.rmtree(tmp)

    def test_unredactable_file_is_excluded_from_the_final_tar(self):
        def fake_dump(base):
            os.makedirs(path.join(base, 'apt', 'sources.list.d'))
            with open(path.join(base, 'apt', 'sources.list.d', 'extra.list.gz'), 'wb') as fp:
                fp.write(b'Serial Number: SECRET123\n')  # not real gzip, just needs to not survive

        SubProcess.reset(mocking=False)
        (tmp, tgz) = util.create_tmp_logs(func=fake_dump)
        extract_dir = path.join(tmp, 'extracted')
        os.mkdir(extract_dir)
        subprocess.run(['tar', '-xzf', tgz, '-C', extract_dir], check=True)
        base = path.join(extract_dir, 'lud-logs')

        self.assertFalse(path.exists(path.join(base, 'apt', 'sources.list.d', 'extra.list.gz')))

        with open(path.join(base, 'metadata.json')) as fp:
            metadata = json.load(fp)
        self.assertEqual(
            metadata['excluded_files'],
            [path.join('apt', 'sources.list.d', 'extra.list.gz')],
        )

        shutil.rmtree(tmp)


class TestDumpLogs(TestCase):
    def _run_dump_logs(self, tmp):
        with patch('system76driver.util.subprocess.run') as run, \
                patch('system76driver.util.determine_model', return_value='test-model'), \
                patch('system76driver.util.distro.name', return_value='test-distro'), \
                patch('system76driver.util.os.uname', create=True) as uname:
            uname.return_value.release = '0.0.0-test'
            run.return_value.stdout = ''
            run.return_value.stderr = ''
            util.dump_logs(tmp.dir)
        return [call.args[0] for call in run.call_args_list]

    def test_reboot_history_does_not_collect_login_history(self):
        # 'last' alone lists every login session, including usernames;
        # 'last reboot' lists only boot/shutdown events.
        commands = self._run_dump_logs(TempDir())
        self.assertIn('last reboot', commands)
        self.assertNotIn('last', commands)

    def test_lsblk_omits_uuid_column(self):
        commands = self._run_dump_logs(TempDir())
        lsblk = next(c for c in commands if c.startswith('lsblk'))
        self.assertNotIn('UUID', lsblk.split(','))

    def test_efibootmgr_is_not_verbose(self):
        commands = self._run_dump_logs(TempDir())
        self.assertIn('efibootmgr', commands)
        self.assertNotIn('efibootmgr -v', commands)

    def test_lsusb_is_not_verbose(self):
        # -vv's descriptor dump is where iSerial values show up; plain
        # lsusb (bus/device/vendor:product/description) is enough for
        # hardware identification.
        commands = self._run_dump_logs(TempDir())
        self.assertIn('lsusb', commands)
        self.assertNotIn('lsusb -vv', commands)

    def test_lspci_uses_nnk_not_verbose(self):
        # -nnk (numeric IDs + kernel driver in use) instead of -vv: same
        # diagnostic value for driver issues, without -vv's verbose
        # capability dump (where a device serial number can show up).
        commands = self._run_dump_logs(TempDir())
        self.assertIn('lspci -nnk', commands)
        self.assertNotIn('lspci -vv', commands)

    def test_does_not_collect_raw_syslog_or_rotated_apt_gz(self):
        tmp = TempDir()
        self._run_dump_logs(tmp)
        collected = {
            path.relpath(path.join(root, name), tmp.dir)
            for root, _dirs, files in os.walk(tmp.dir) for name in files
        }
        self.assertNotIn('syslog', collected)
        self.assertFalse(any(name.endswith('.gz') for name in collected))
