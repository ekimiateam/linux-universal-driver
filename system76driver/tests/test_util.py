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
import os
from os import path
import shutil

from .helpers import TempDir
from system76driver.mockable import SubProcess
from system76driver import util


class TestFunctions(TestCase):
    def test_logs_do_not_follow_existing_symlinks_or_overwrite_previous_logs(self):
        tmp = TempDir()
        victim = tmp.write(b'Keep this file unchanged', 'important.conf')
        os.symlink(victim, tmp.join('lud-logs.tgz'))
        first = util.create_logs(tmp.dir, func=None)
        second = util.create_logs(tmp.dir, func=None)
        self.assertNotEqual(first, second)
        self.assertTrue(path.isfile(first))
        self.assertTrue(path.isfile(second))
        with open(victim, 'rb') as fp:
            self.assertEqual(fp.read(), b'Keep this file unchanged')

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
        self.assertTrue(path.isdir(path.join(tmp, 'lud-logs')))
        shutil.rmtree(tmp)

    def test_create_logs(self):
        SubProcess.reset(mocking=False)
        tmp = TempDir()
        tgz = util.create_logs(tmp.dir, func=None)
        self.assertEqual(path.dirname(tgz), tmp.dir)
        self.assertTrue(path.basename(tgz).startswith('lud-logs-'))
        self.assertTrue(tgz.endswith('.tgz'))
        self.assertEqual(os.stat(tgz).st_mode & 0o777, 0o600)
        self.assertTrue(path.isfile(tgz))

