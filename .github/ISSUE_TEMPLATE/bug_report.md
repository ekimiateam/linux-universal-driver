---
name: Bug report
about: Report a driver, restore, or installation failure in Linux Universal Driver
title: '[Bug] '
labels: 'bug'
assignees: ''

---

<!--
If this is a question or general discussion topic rather than a reproducible bug, please open a
discussion or reach out to the ekimia team directly instead — issues here are for tracking
concrete driver/installer defects.
-->

## Summary

Describe what LUD did, what you expected instead, and whether the affected hardware feature
(audio, backlight, touchpad, boot, etc.) still works after a reboot.

## System details

- Distribution (`cat /etc/os-release`):
- Package version (`apt policy system76-driver` or `apt policy linux-universal-driver`):
- Machine model (Product Name / Board Name, e.g. `dmidecode -s system-product-name`):
- Manufacturer: System76 / Ekimia / Apple / other

## Steps to reproduce

1.
2.
3.

## Expected behavior

## Actual behavior

## Logs

Attach the output of `system76-driver-cli --logs <dir>`, or the GUI's "Create Log Files" button,
if you have it. Redact hostnames, serial numbers, and other identifying values first — the
collected archive is not sanitized automatically yet (see #25).

## Other notes
