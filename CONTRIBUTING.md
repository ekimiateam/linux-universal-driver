# Contributing to Linux Universal Driver

This document is a map, not a rulebook: where things live, and where to look next.

## Repo map

LUD is a Python package plus a handful of thin entry points, packaged as a `.deb`.

| Path | What it is |
|---|---|
| `system76driver/products.py` | The supported-machine registry: board/product IDs mapped to the actions each one needs |
| `system76driver/actions.py` | The `Action` classes products declare — GRUB/kernelstub kernel params, gsettings overrides, DKMS/APT driver installs, quirks |
| `system76driver/model.py` | Hardware identification: DMI lookups, model detection |
| `system76driver/util.py` | Log collection (`dump_logs`/`create_logs`) and other shared helpers |
| `system76driver/daemon.py`, `userdaemon.py` | The system and per-user D-Bus daemons |
| `system76driver/gtk.py` | The GTK UI |
| `system76driver/data/` | Bundled assets: icons, firmware, and vendor-supplied `.deb`s for out-of-tree drivers (tuxedo, facetimehd) |
| `system76-driver`, `system76-driver-cli` | GUI and CLI entry points, both built on `ActionRunner` in `actions.py` |
| `system76-daemon`, `system76-user-daemon`, `system76-virtual-hub`, `system76-nm-restart`, `system76-thunderbolt-reload` | The other installed entry points; most are thin wrappers invoking the package |
| `quirks/` | Per-model files, e.g. NVIDIA quirks, installed alongside the matching product |
| `dmi-test/` | DMI fixtures used to exercise model detection without real hardware |
| `po/` | Translatable strings (`.po`/`.pot`) |
| `debian/` | Packaging: control, postinst, systemd/upstart units, the polkit policy |

### Tests

`system76driver/tests/` covers detection, actions, the daemons, and the GTK UI. Run them with
`pytest` from the repo root; CI (`.github/workflows/python-app.yml`) runs the same command plus
`flake8`.

## Workflow

- Development targets the `develop` branch; releases are cut from `master`
  (`./bump-version.py`, then `./make-release.py` — see the README's "Making changes" section).
- Sign off commits (`git commit -s`) per the Developer Certificate of Origin. CI flags commits
  missing the trailer as a warning; it's a recommendation, not a gate.
- If a tool helped write part of a change, say so with an `Assisted-by:`/`Generated-by:` commit
  trailer (see the pull request template) rather than `Co-authored-by:`, which implies a human
  co-author.
- Run `flake8 . --max-line-length=127` and `pytest` before opening a PR — CI runs the same checks.
