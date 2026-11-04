# Branding

Shared with kilnlinux.org and the original Kiln Linux project.

- Mark: the striped triangle, `mark-triangle.svg` (dark, for light
  backgrounds) and `mark-triangle-light.svg` (light, for dark backgrounds).
  Flat, one color: `#1A1A1A` on light, `#EDEDED` on dark. In plain text the
  mark is `▲`. Secondary marks: `mark-wave*`, `mark-k*`.
- Accent: kiln brick `#a4471f` (truecolor ANSI `38;2;164;71;31`, also
  `ANSI_COLOR` in os-release). Background `#1a1a1a`, text `#ededed`.
- The Linux text console has 16 colors; there the brick shows as red.

Derived from the mark; update them when it changes:

- `archiso/kiln/airootfs/usr/share/kiln/logo`: the mark in ASCII, from the
  original Kiln Linux, used by fastfetch (`/etc/xdg/fastfetch/config.jsonc`).
- `splash.svg` to `archiso/kiln/syslinux/splash.png` (BIOS boot menu):
  `rsvg-convert branding/splash.svg -o archiso/kiln/syslinux/splash.png`
- Terminal output: `::` headings in the accent, everything else plain.
  Color only on a TTY, and never when `NO_COLOR` is set.

Used in: `archiso/kiln/airootfs/etc/motd`, `airootfs/etc/kiln/os-release`,
boot menu titles and colors, `kiln` (`src/ui.rs`), `kiln-install`, `configs/*`,
`packages/twmx/config.h` (border and dmenu colors).
