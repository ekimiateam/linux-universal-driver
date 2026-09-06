# Bundled driver fixes

These patches describe the source changes inside the two bundled Debian packages.
They apply to the packages from commit `835c165a73f05c319ec12037d90486be8d068e89`.

| Package | Original version | Patched version |
| --- | --- | --- |
| tuxedo-yt6801 | 1.0.31-8 | 1.0.31-8+ekimia1 |
| tuxedo-drivers | 4.11.2 | 4.11.2+ekimia1 |

The YT6801 patch requires administrator privileges for private diagnostic commands
and validates their buffers before accessing them. The Tuxedo patch drains NB05
timer/work callbacks before removal and adapts the timer and CPU identifiers to
Linux 6.15. Comments in the patches link to the kernel documentation and sources.
Both the Debian and DKMS versions change so an existing installation rebuilds its
modules instead of retaining the old binaries.

To rebuild a package, run the following from the repository root with a new work
directory. The example is for YT6801; use the corresponding name, archive and
version from the table for Tuxedo drivers. No driver is installed by these steps.

```sh
package=tuxedo-yt6801
archive=tuxedo-yt6801_latest.deb
version=1.0.31-8
base=835c165a73f05c319ec12037d90486be8d068e89
mkdir driver-rebuild
git show "$base:system76driver/data/$archive" > driver-rebuild/original.deb
dpkg-deb --raw-extract driver-rebuild/original.deb driver-rebuild/package
patch -d driver-rebuild/package -p1 < "driver-patches/$package.patch"
mv "driver-rebuild/package/usr/src/$package-$version" \
   "driver-rebuild/package/usr/src/$package-$version+ekimia1"
(
    cd driver-rebuild/package
    find . -path ./DEBIAN -prune -o -type f -printf '%P\0' \
        | LC_ALL=C sort -z | xargs -0 md5sum > DEBIAN/md5sums
)
SOURCE_DATE_EPOCH=$(git show -s --format=%ct "$base") \
    dpkg-deb --root-owner-group --build driver-rebuild/package "driver-rebuild/$archive"
```

Compilation checks cover Linux 6.12 and 6.15. Hardware behavior, module unload
races and Secure Boot enrollment still require testing on the affected machines.
