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
Detect actual system capabilities instead of trusting a distro name.

`GrubAction` (see `actions.py`) used to pick its backend by checking one
hardcoded path for `kernelstub`, with no real "neither is available" case.
`boot_backend()` centralizes that same kind of check; `has_command()` is
the same pattern generalized so other actions can depend on it too.
"""

import os
import shutil


# The GTK UI runs ActionRunner as the unprivileged desktop user, before it
# launches the privileged CLI that actually applies anything; if that
# user's PATH happens to omit /usr/sbin (common for non-root shells),
# has_command() must not disagree with what the root CLI would see there.
# Search PATH plus these regardless of what the caller's PATH contains.
_SYSTEM_PATH_DIRS = (
    '/usr/local/sbin', '/usr/local/bin',
    '/usr/sbin', '/usr/bin',
    '/sbin', '/bin',
)


def has_command(name):
    """Return True if `name` is an executable on PATH or a standard system directory."""
    # An empty PATH entry means "current directory" to shutil.which() (same
    # as a shell), so an unset/empty PATH must not turn into a leading ':'
    # that lets a same-named file in the caller's cwd shadow the real one.
    caller_dirs = [entry for entry in os.environ.get('PATH', '').split(os.pathsep) if entry]
    search_path = os.pathsep.join([*caller_dirs, *_SYSTEM_PATH_DIRS])
    return shutil.which(name, path=search_path) is not None


def boot_backend():
    """
    Return 'kernelstub', 'grub', or None if neither's tooling is present.

    Checks for the command each backend is actually applied with
    (`kernelstub`, `update-grub`), the same kind of check `has_command()`
    makes, rather than assuming grub whenever kernelstub is absent.
    """
    if has_command('kernelstub'):
        return 'kernelstub'
    if has_command('update-grub'):
        return 'grub'
    return None
