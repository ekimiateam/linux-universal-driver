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
Collect logs and other info for support.
"""

import json
import os
from os import path
import shutil
import tempfile
import distro
import subprocess
import re
import socket
import ipaddress

from .model import *

_IPV6_CANDIDATE_RE = re.compile(rb'\b(?:[0-9A-Fa-f]{1,4})?(?:::?[0-9A-Fa-f]{1,4}){2,7}(?::[0-9A-Fa-f]{1,4})?\b')


def _redact_ipv6_candidate(match):
    token = match.group(0)
    try:
        ipaddress.IPv6Address(token.decode('ascii'))
    except (ValueError, UnicodeDecodeError):
        return token
    return b'<ip>'


_QUOTED_RE = re.compile(rb"'[^'\n]*'")
# NetworkManager logs an SSID quoted, on a line that also names what it is
# ("connection", "access point", "ssid"): "Activation: (wifi) connection
# 'Home-WiFi' enable...", "Config: added 'ssid' value 'Home-WiFi' (9 bytes)".
# Redacting every quoted token on such a line (rather than trying to pick
# out only the SSID) also catches the literal 'ssid'/'connection' label
# some of these messages quote, which is a harmless over-redaction.
_WIFI_LINE_RE = re.compile(rb'(?i)^.*\b(?:wifi|ssid|access point)\b.*$', re.MULTILINE)


def _redact_wifi_line(match):
    return _QUOTED_RE.sub(b"'<ssid>'", match.group(0))


# Every replacement below is a fixed literal placeholder, never the
# matched value, so nothing sensitive can leak back in through the
# substitution itself.
_REDACTIONS = [
    # "Serial Number: X", "serial: X", "iSerial: X" - label/value on one line.
    (re.compile(rb'^([ \t]*(?:i?Serial(?: Number)?|UUID|Asset Tag)[ \t]*:[ \t]*).+$',
                re.IGNORECASE | re.MULTILINE),
        rb'\1<redacted>'),
    # same labels without a colon: lsusb -vv's "iSerial <index> <value>" and
    # lspci -vv's "Device Serial Number <value>" capability line. requires a
    # digit somewhere in the value so plain prose ("the serial number was
    # five") isn't touched.
    (re.compile(rb'((?:Device )?(?:i?Serial(?: Number)?)\b[ \t]+(?:\d+[ \t]+)?)'
                rb'((?=\S*\d)[\w:-]+)',
                re.IGNORECASE),
        rb'\1<redacted>'),
    (re.compile(rb'\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-'
                rb'[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b'),
        rb'<uuid>'),
    # /etc/fstab and /etc/crypttab identify devices by UUID=/PARTUUID=; the
    # short MBR-style PARTUUID form (e.g. 9e1e7f3c-01) isn't a full UUID
    # and would otherwise pass the generic UUID pattern above untouched.
    (re.compile(rb'\b((?:PART)?UUID=)[0-9A-Fa-f-]+', re.IGNORECASE),
        rb'\1<uuid>'),
    (re.compile(rb'\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b'),
        rb'<mac>'),
    (re.compile(rb'\b(?!127\.0\.0\.1\b)(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)'
                rb'{3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
        rb'<ip>'),
    (_IPV6_CANDIDATE_RE, _redact_ipv6_candidate),
    # matches with or without a trailing slash, so "/home/alice" at the end
    # of a line is covered as well as "/home/alice/.config/foo.conf".
    (re.compile(rb'/home/[^/\s]+(/?)'),
        rb'/home/<user>\1'),
    (_WIFI_LINE_RE, _redact_wifi_line),
    # unquoted "SSID: <name>" form (iwconfig/iw/nmcli-style), separate from
    # the quoted NetworkManager-journal forms _WIFI_LINE_RE handles above.
    (re.compile(rb'^([ \t]*SSID:[ \t]*).+$', re.IGNORECASE | re.MULTILINE),
        rb'\1<ssid>'),
    # apt history's "Requested-By: <user> (<uid>)" - keep the rest of the
    # transaction record (packages, timestamps), drop just the identity.
    (re.compile(rb'^([ \t]*Requested-By:[ \t]*).+$', re.IGNORECASE | re.MULTILINE),
        rb'\1<redacted>'),
    # apt source URL userinfo (deb https://user:pass@host/repo ...) - drop
    # the credentials, keep the host/path that's actually useful to know.
    (re.compile(rb'(https?://)[^/\s@]+:[^/\s@]+@'),
        rb'\1<redacted>@'),
    # "Authorization: <scheme> <value>" - redact the whole value regardless
    # of scheme (Bearer/Basic/...), since \S+ below would only take the
    # scheme word and leave the actual token exposed.
    (re.compile(rb'^([ \t]*Authorization:[ \t]*).+$', re.IGNORECASE | re.MULTILINE),
        rb'\1<redacted>'),
    (re.compile(rb'(password|passwd|token|apikey|api_key|secret)([ \t]*[:=][ \t]*)\S+',
                re.IGNORECASE),
        rb'\1\2<redacted>'),
]


def redact_text(data):
    """
    Replace known-sensitive patterns in `data` (bytes) with fixed placeholders.
    """
    for pattern, replacement in _REDACTIONS:
        data = pattern.sub(replacement, data)
    hostname = socket.gethostname().encode()
    if hostname:
        data = data.replace(hostname, b'<hostname>')
    return data


def redact_logs(base):
    """
    Rewrite every file under `base` in place, redacting known-sensitive
    patterns. A file this can't safely redact (currently: .gz, binary and
    unsafe to rewrite as text) is removed from `base` outright rather than
    left in place unredacted - a privacy-safe-by-default bundle can't rely
    on metadata alone to document what it failed to clean. Returns the
    base-relative paths of anything removed, so callers can record it.
    """
    excluded = []
    for root, _dirs, files in os.walk(base):
        for name in files:
            fp = path.join(root, name)
            if name.endswith('.gz'):
                excluded.append(path.relpath(fp, base))
                os.remove(fp)
                continue
            with open(fp, 'rb') as f:
                data = f.read()
            redacted = redact_text(data)
            if redacted != data:
                with open(fp, 'wb') as f:
                    f.write(redacted)
    return excluded


def dump_command(base, name, args):
    fp = open(path.join(base, name), 'xt')
    output = subprocess.run(" ".join(args), capture_output=True, shell=True, text=True)
    fp.write(output.stdout + "\n" + output.stderr)


def dump_path(base, name, src):
    if path.exists(src):
        dst = path.join(base, name)
        dst_dir = path.dirname(dst)
        if not path.isdir(dst_dir):
            os.makedirs(dst_dir)
        assert not path.exists(dst)
        if path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy(src, dst)


JOURNAL_UNITS = ('NetworkManager', 'systemd-suspend')
JOURNAL_IDENTIFIERS = ('dkms', 'system76-daemon')


def dump_journal(base):
    """
    Collect journalctl output scoped to hardware/driver-relevant units and
    identifiers, instead of the whole system journal. Separate
    invocations per category rather than one combined match expression:
    journalctl ANDs different match-field types by default, and getting
    that boolean grouping wrong would silently drop a whole category
    (e.g. all kernel messages) rather than error visibly.
    """
    since = ['--since', 'yesterday']
    dump_command(base, 'journalctl-kernel', ['journalctl', '-k'] + since)
    for unit in JOURNAL_UNITS:
        dump_command(base, 'journalctl-' + unit, ['journalctl', '-u', unit] + since)
    for ident in JOURNAL_IDENTIFIERS:
        dump_command(base, 'journalctl-' + ident, ['journalctl', '-t', ident] + since)


def dump_logs(base):
    fp = open(path.join(base, 'systeminfo.txt'), 'x')
    fp.write(' Model: {}\n'.format(determine_model()))
    fp.write('OS Version: {}\n'.format(distro.name(pretty=True)))
    fp.write('Kernel Version: {}\n'.format(os.uname().release))

    dump_command(base, "boot-process-times", ["systemd-analyze", "blame"])
    dump_command(base, "free-disk-space", ["df", "-h"])
    dump_command(base, "dmesg", ["dmesg"])
    dump_command(base, "dmidecode", ["dmidecode"])
    dump_command(base, "efibootmgr", ["efibootmgr"])
    dump_journal(base)
    dump_command(base, "lsblk", ["lsblk", "-o", "NAME,MODEL,FSTYPE,FSVER,SIZE,FSUSE%,MOUNTPOINTS,LABEL"])
    dump_command(base, "lsmod", ["lsmod"])
    # -nnk / plain instead of -vv: numeric vendor/device IDs and the kernel
    # driver in use cover hardware/driver diagnosis without the verbose
    # descriptor dumps (which is where device serial numbers show up).
    dump_command(base, "lspci", ["lspci", "-nnk"])
    dump_command(base, "lsusb", ["lsusb"])
    dump_command(base, "reboot-history", ["last", "reboot"])
    dump_command(base, "sensors", ["sensors"])
    dump_command(base, "upower", ["upower"])
    dump_command(base, "uptime", ["uptime"])
    dump_command(base, "xinput", ["xinput"])
    dump_path(base, "crypttab", "/etc/crypttab")
    dump_path(base, "kernelstub", "/etc/kernelstub/configuration")
    dump_path(base, "fstab", "/etc/fstab")
    dump_path(base, "Xorg.log", "/var/log/Xorg.0.log")
    dump_path(base, "apt/sources.list", "/etc/apt/sources.list")
    dump_path(base, "apt/sources.list.d", "/etc/apt/sources.list.d")
    dump_path(base, "apt/history", "/var/log/apt/history.log")
    dump_path(base, "apt/term", "/var/log/apt/term.log")


EXCLUDED_CATEGORIES = [
    "serial_numbers", "uuids", "mac_addresses", "hostname",
    "home_paths", "ip_addresses", "credentials", "wifi_ssids",
    "user_identity",
]


def write_metadata(base, excluded_files=()):
    """
    Write a small manifest documenting what the bundle collected and
    what was redacted. `collectors` reflects the directory's actual
    contents at write time rather than a static list, so it can't drift
    out of sync with dump_logs()/dump_journal(). `excluded_files` names
    anything redact_logs() removed from the bundle rather than risk
    leaving it unredacted (currently: .gz files) - it documents a bundle
    that's already clean, it isn't what makes the bundle clean.
    """
    collectors = sorted(
        path.relpath(path.join(root, name), base)
        for root, _dirs, files in os.walk(base)
        for name in files
    )
    metadata = {
        "format_version": 1,
        "redacted": True,
        "collectors": collectors,
        "excluded_categories": EXCLUDED_CATEGORIES,
        "excluded_files": sorted(excluded_files),
    }
    with open(path.join(base, 'metadata.json'), 'w') as fp:
        json.dump(metadata, fp, indent=2)
        fp.write('\n')


def create_tmp_logs(func=dump_logs):
    tmp = tempfile.mkdtemp(prefix='logs.')
    base = path.join(tmp, 'lud-logs')
    os.mkdir(base)
    if func is not None:
        func(base)
    excluded_files = redact_logs(base)
    write_metadata(base, excluded_files)
    tgz = path.join(tmp, 'lud-logs.tgz')
    cmd = [
        'tar', '-czv',
        '-f', tgz,
        '-C', tmp,
        'lud-logs',
    ]
    subprocess.run(cmd)
    return (tmp, tgz)


def create_logs(homedir, func=dump_logs):
    (tmp, src) = create_tmp_logs(func)
    assert path.isdir(homedir)
    dst = path.join(homedir, path.basename(src))
    shutil.copy(src, dst)
    shutil.rmtree(tmp)
    return dst


def send_logs():
    dst = path.join(os.environ['HOME'], "lud-logs.tgz")
    print(dst)
    hostname = subprocess.run('hostname', capture_output=True, shell=True, text=True).stdout.strip()
    desturl = "https://drive.ekimia.fr/public.php/webdav/"+hostname+"-lud-logs.tgz"
    Curlcmd = "curl -verbose -X PUT -u 'publicupload:' -T "+dst+" "+desturl
    print(Curlcmd)
    status, output = subprocess.getstatusoutput(Curlcmd)
    print(output)
