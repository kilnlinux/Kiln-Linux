# Kiln Linux

A minimal Arch Linux based distribution: Arch's repositories and pacman,
a small live ISO with a Void-style installer, a choice of desktops (twmx by default), and
`kiln`, a tool that keeps your package sets in readable profile files.

| Component | Choice |
|---|---|
| Base | Arch Linux (official repositories, pacman) |
| Init | systemd |
| Desktop | [twmx](https://github.com/arcbaseproject/twmx) on X11 (default); i3, Sway, Hyprland, XFCE, KDE Plasma, GNOME, or none |
| Network | NetworkManager (installed), systemd-networkd + iwd (live ISO) |
| Audio (optional) | PipeWire |
| Login | window managers start on tty1 login; XFCE, Plasma, GNOME get a login screen |
| Boot | systemd-boot (installed, UEFI); ISO boots UEFI and BIOS |

## Quick start

```sh
sudo pacman -S --needed archiso rust base-devel git   # build deps
make test                                 # checks, no root
make iso                                  # out/kilnlinux-YYYY.MM.DD-x86_64.iso, no root
sudo pacman -S --needed qemu-desktop edk2-ovmf
make run                                  # boot it in QEMU (UEFI) with a blank disk
```

In the live system (auto-login as root), run `kiln-install`.
After installing, `make run-disk` boots the installed disk.

## Layout

```text
archiso/kiln/      archiso profile (derived from upstream releng)
packages/kiln/     the kiln CLI (Rust)
packages/kiln-install/kiln-install   the installer (bash + dialog)
packages/twmx/     PKGBUILD + Kiln config.h for twmx, built into the [kiln] repo
profiles/          core; twmx, i3, sway, hyprland, xfce, plasma, gnome; developer, audio
configs/           home skeleton: .xinitrc, .Xresources, .config/* (goes to /etc/skel)
scripts/           build.sh, test.sh, qemu.sh
docs/              architecture, kiln, installing, testing
branding/          marks (SVG), logo generator, boot splash
```

## Documentation

- [docs/architecture.md](docs/architecture.md): how the pieces fit, and why; modifying the distribution
- [docs/kiln.md](docs/kiln.md): using `kiln` and pacman, writing profiles
- [docs/install.md](docs/install.md): building, QEMU, installing
- [docs/testing.md](docs/testing.md): what is tested, and how to measure resource use
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Status

Builds rootless with archiso; `make test` passes; `make e2e` installs the ISO
in QEMU unattended (UEFI, twmx) and boots the result to a working twmx
session. See docs/testing.md for what has and has not been verified.

Known limits: the installer is UEFI-only (the ISO itself boots on BIOS); no
disk encryption option; `kiln` is copied into place, not installed as a
pacman package; `[kiln]` packages (twmx) update only with a new ISO.

## License

MIT (see LICENSE), except `archiso/kiln/`, which is derived from archiso's
releng profile and is GPL-3.0-or-later like archiso.
