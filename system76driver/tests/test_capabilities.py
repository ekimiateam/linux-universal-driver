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
Unit tests for `system76driver.capabilities` module.
"""

import os
from unittest import TestCase
from unittest.mock import patch

from system76driver import capabilities


class TestHasCommand(TestCase):
    def test_present(self):
        with patch('shutil.which', return_value='/usr/bin/glib-compile-schemas'):
            self.assertTrue(capabilities.has_command('glib-compile-schemas'))

    def test_absent(self):
        with patch('shutil.which', return_value=None):
            self.assertFalse(capabilities.has_command('glib-compile-schemas'))

    def test_does_not_assume_a_familiar_command_name(self):
        # An unfamiliar distro that genuinely provides the command should
        # pass, and a familiar distro missing it should not; has_command()
        # only ever asks the filesystem, never a distro name.
        with patch('shutil.which', return_value='/opt/unfamiliar-distro/bin/ethtool'):
            self.assertTrue(capabilities.has_command('ethtool'))

    def test_empty_path_does_not_add_a_cwd_lookup(self):
        # An empty PATH entry means "current directory" to shutil.which(),
        # same as a shell; an unset/empty PATH must not turn into a
        # leading ':' that lets a same-named file in the cwd shadow the
        # real system executable.
        with patch.dict(os.environ, {'PATH': ''}), \
                patch('shutil.which', return_value=None) as which:
            capabilities.has_command('update-grub')
        search_path = which.call_args.kwargs['path']
        self.assertNotIn('', search_path.split(os.pathsep))
