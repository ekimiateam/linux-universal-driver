# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['linux_universal_driver.py'],
    pathex=[],
    binaries=[],
    datas=[('system76-driver', '.'), ('system76-driver-cli', '.'), ('system76driver', 'system76driver')],
    hiddenimports=['distro', 'gi.repository.GLib', 'gi.repository.Gtk'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='linux-universal-driver',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
