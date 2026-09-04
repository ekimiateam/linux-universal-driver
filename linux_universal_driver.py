#!/usr/bin/env python3
"""Entry point used by the single-file distribution.

``--cli`` is an internal switch used by the GUI when it starts a privileged
command.  Keeping both entry points in one executable is necessary for a
PyInstaller one-file build.
"""

from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

# The application's driver actions intentionally use relative paths to its
# bundled firmware and .deb files.  PyInstaller extracts those resources here.
if getattr(sys, "frozen", False):
    os.chdir(ROOT)

if len(sys.argv) > 1 and sys.argv[1] == "--cli":
    del sys.argv[1]
    target = ROOT / "system76-driver-cli"
else:
    target = ROOT / "system76-driver"

runpy.run_path(str(target), run_name="__main__")
