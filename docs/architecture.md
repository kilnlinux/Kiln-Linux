# How Kiln Linux works

Kiln Linux is Arch Linux plus four things: a live ISO profile, an installer,
a set of package profiles, and the `kiln` tool that applies them. Nothing
replaces pacman, systemd or the Arch repositories. An installed Kiln system
is an Arch system you can run `pacman -Syu` on, with a different
`os-release`, some defaults, and `kiln`.

## The live ISO (`archiso/kiln`)

archiso builds ISOs from a *profile* directory:

| File | Purpose |
|---|---|
| `profiledef.sh` | ISO name, label, boot modes, file permissions |
| `packages.x86_64` | packages installed into the live system |
| `pacman.conf` | repositories used for the build (official Arch) |
| `airootfs/` | files copied over the live root filesystem |
| `syslinux/` | BIOS boot menu |
| `efiboot/` | UEFI boot menu (systemd-boot entries) |
| `grub/` | only used for GRUB boot modes; kept from upstream, unused |

The profile is a copy of upstream `releng` (`/usr/share/archiso/configs/releng`)
with:

- packages cut from 128 to about 45: installer needs, disk rescue, network,
  accessibility (speech boot entry, brltty, espeakup), console tools;
- services removed: VM guest agents, ModemManager, cloud-init, sshd (still
  installed, start it with `systemctl start sshd`);
- bash instead of zsh for root;
- Kiln branding: boot menus, `/etc/motd`, `/etc/hostname`, os-release.

`make iso` (`scripts/build.sh`) does not modify `archiso/kiln`. It copies it
to `build/profile`, adds `kiln`, `kiln-install`, the profiles and configs into
that copy's `airootfs`, and runs `mkarchiso` on the copy. That keeps the
binary out of git and the source profile identical to what you read.

**Rootless builds.** archiso can build as a normal user: it runs pacstrap
and file operations inside a user namespace (`unshare --map-auto
--map-root-user`), where your user appears as root and your subordinate IDs
(`/etc/subuid`) back the other users. That is why `build/work` contains
files you cannot delete directly, and why `make clean` deletes it through
`unshare`.

**os-release.** `/etc/os-release` is a symlink to `/usr/lib/os-release`,
owned by Arch's `filesystem` package. Overwriting it in `airootfs` would
conflict with that package during the build, and any later upgrade of
`filesystem` would bring Arch's file back. Instead, a pacman hook
(`airootfs/etc/pacman.d/hooks/kiln-os-release.hook`) copies
`/etc/kiln/os-release` over it after every install or upgrade of
`filesystem`. The same hook is installed on the target system.

## The installer (`packages/kiln-install/kiln-install`)

A bash script with a `dialog` interface in the style of Void Linux's
installer (and based on the original Kiln Linux's): a main menu lists every
setting (keyboard, network, hostname, locale, time zone, root, user, desktop,
extras, disk, boot loader) with its current value; you visit them in any
order, then choose Install. Bash, because every step is a call to an
existing tool (`sfdisk`, `mkfs`, `pacstrap`, `genfstab`, `arch-chroot`,
`bootctl`), and a shell script shows those calls directly.

1. **Settings**: nothing on disk changes. The live medium is not offered as
   a target, disks with mounted filesystems are refused, and Install checks
   every setting first (`settings_problem`). The summary shows what will be
   erased; erasing a disk needs its name typed back.
2. **Install**: `install_all` runs in a subshell with `set -e`; its output
   scrolls in a progress box and goes to `/tmp/kiln-install.log`. Any failing
   command stops it and the installer shows *Installation FAILED* with the
   end of the log. It never reports success unless `validate` passes.

`kiln-install --config FILE` skips the menus: FILE sets the same variables
(see the top of the script) and the install runs unattended. That is how the
QEMU tests drive it.

Desktops are a table at the top of the script (`DESKTOPS`): each entry names
its kiln profile, the display manager to enable, if any, and how to start it.
Window managers (twmx, i3, sway, Hyprland) start from a TTY; desktop
environments (XFCE, Plasma, GNOME) get their login screen enabled.

Install steps: GPT with a 1 GiB EFI system partition and a root partition;
`pacstrap -K` of `base`, the chosen kernels, `linux-firmware`, `sof-firmware`, CPU microcode and filesystem
tools; `genfstab -U`; time zone, locale, keymap, hostname; `kiln apply` of
each chosen profile inside the chroot; user with sudo, root locked or with
the password you chose;
`mkinitcpio -P`; the boot loader; then checks for the kernel, initramfs,
boot loader, root UUID in the boot entry and fstab, the user, os-release and
`kiln doctor`.

Boot loaders: all three boot the kernel and initramfs from the FAT32
partition mounted at `/boot` (the EFI system partition; on BIOS the same
kind of partition, plus a 1 MiB BIOS boot partition for the loader's stage 2).

| | systemd-boot | GRUB | Limine |
|---|---|---|---|
| Firmware | UEFI | UEFI, BIOS | UEFI, BIOS |
| Config | `/boot/loader/entries/kiln.conf` | `/etc/default/grub`, then `grub-mkconfig` | `/boot/limine.conf` |
| Kept current by | `systemd-boot-update.service` | `/etc/pacman.d/hooks/kiln-grub.hook` | `/etc/pacman.d/hooks/kiln-limine.hook` |

systemd-boot is the UEFI default: it ships with systemd (no extra package)
and its config is three short text files. GRUB is the BIOS default. Arch
itself never reinstalls GRUB or Limine to the disk after a package upgrade;
Kiln's pacman hooks do, so the loader on the disk matches its package.
Kernel upgrades need nothing: the kernel and initramfs keep their file names.

Why profiles are applied with `kiln` during install: the installed system
then has correct kiln state from the start, so `kiln remove twmx --purge`
works on day one.

## Profiles and `kiln`

See [kiln.md](kiln.md) for usage. Design in brief:

- **pacman is the only package database.** kiln asks pacman everything:
  `pacman -T` for "is this satisfied" (it understands provides and versions),
  `-Qq` for installed names, `-Slq` for repository names, `-S`/`-R` for
  changes. kiln never reads `/var/lib/pacman` itself.
- **kiln's own state is small**: `/var/lib/kiln/state.toml` lists active
  profiles and, for each, the packages kiln itself installed. Packages that
  were already present when you applied a profile are not recorded, so
  `kiln remove --purge` can never remove something you installed yourself.
- **State is written after pacman succeeds**, by atomic rename. If pacman
  fails or you answer "n", kiln records nothing.
- **No rollback is claimed.** pacman transactions are all-or-nothing on their
  own; kiln adds no undo beyond that.
- **No `-Sy`.** Refreshing the package databases without upgrading is a
  partial upgrade, which Arch does not support. Run `sudo pacman -Syu`.

Source layout (`packages/kiln/src`):

| Module | Job |
|---|---|
| `main.rs` | dispatch, exit codes, SIGPIPE |
| `cli.rs` | argument parsing and help text |
| `manifest.rs` | TOML parsing, validation, profile search paths |
| `pacman.rs` | every pacman call; root check |
| `plan.rs` | pure planning rules (what to install, what is safe to remove) |
| `apply.rs` | `apply` and `remove` |
| `state.rs` | `/var/lib/kiln/state.toml` |
| `commands.rs` | read-only commands, `profile create`, `export` |
| `ui.rs`, `error.rs` | output colors, the error type |

Dependencies: `serde` and `toml`. Arguments are parsed by hand: twelve
commands and three flags do not justify a framework.

**Adding a package source later** (for example a local repository or
verified binary packages): add an optional field to `Packages` in
`manifest.rs` (unknown fields are errors today, so old kiln versions reject
manifests they cannot honor), plan it in `plan.rs`, and run it in `apply.rs`.
The `official` path stays unchanged. Sources that build third-party code
(AUR PKGBUILDs) should never run automatically.

## The desktop

The default desktop, the `twmx` profile, is X11 with [twmx](https://github.com/arcbaseproject/twmx),
a one-file tiling window manager grown out of TinyWM: xterm (Super+Return),
dmenu (Super+d), dunst for notifications and polybar, nothing else running.
twmx has no bar of its own, but it reserves the space of dock windows and
publishes its workspaces over EWMH, which polybar's `xworkspaces` module
reads, so the bar needs no twmx changes. twmx has no runtime config; its
config is a C header compiled in, so Kiln's colors and keys live in
`packages/twmx/config.h`.

### Theme: Kiln Graphite

Every desktop Kiln configures (twmx, i3, sway, Hyprland) shares one theme,
`themes/graphite`: charcoal `#1a1a1a`, a warm graphite surface `#242322` for
menus and notifications, `#34322f` for unfocused borders and separators,
`#ededed` text with `#8c8780` for secondary text, and the kiln brick
`#a4471f` as the single accent. The accent marks only focus: the focused
window's border, the current workspace, the selected launcher entry. Borders
are 2 px, gaps 6 px, bars 22 px with a 1 px line under them, all text DejaVu
Sans Mono 10 (sans for launcher and notifications). No rounding, blur,
shadows or animations.

Files in `configs/` contain `@name@` where a theme value goes (`#@accent@`,
`@gap@`). `scripts/build.sh` copies `configs/` into the ISO and runs
`scripts/render-theme.sh themes/graphite` on the copy; `make test` renders
it too and fails on any name the theme doesn't define. twmx's `config.h` is
compiled, so it holds literal colors; the test checks they are Graphite's.

To add a theme: copy `themes/graphite` and change the values. There is no
theme switcher yet: render a theme by hand with
`scripts/render-theme.sh themes/NAME DIR` on a copy of `configs/`.

XFCE, Plasma and GNOME keep their own themes; GTK apps elsewhere get the
dark variant of Adwaita (`~/.config/gtk-3.0/settings.ini`).

### Keys

The same in twmx, i3, sway and Hyprland unless noted:

| Keys | Action |
|---|---|
| Super+Return | terminal |
| Super+d | launcher |
| Super+q | close window |
| Super+h/j/k/l | focus left/down/up/right (twmx: j/k cycle focus, h/l resize the master area) |
| Super+Shift+h/j/k/l | move window (twmx: Shift+j/k) |
| Super+1–9 | go to workspace |
| Super+Shift+1–9 | move window to workspace |
| Super+Shift+Space | toggle floating |
| Super+f | fullscreen |
| Super+Escape | lock the screen |
| Print, Shift+Print | screenshot of the screen, or of a region, to ~/Pictures/Screenshots |
| Super+Shift+e | exit (twmx: Super+Shift+q) |

twmx is not in the Arch repositories, so Kiln builds it:

1. `packages/twmx/PKGBUILD` fetches a pinned commit and builds with Kiln's
   `config.h`. `make iso` runs `makepkg` on every `packages/*/PKGBUILD` and
   `repo-add`s the results into `build/repo`, a pacman repository named
   `[kiln]`.
2. The repository is copied onto the ISO at `/usr/share/kiln/repo`.
3. The installer copies it to the new system and adds `[kiln]` to its
   `pacman.conf`, so the profile's `twmx` installs through pacman like any
   other package.

`[kiln]` is unsigned (`SigLevel = Optional TrustAll`), acceptable only
because it is a local, root-owned directory. Its packaged binaries update when
you install from a newer Kiln ISO; hosting it online, signed, is the upgrade
path. twmx also ships the upstream self-updater and a daily systemd user
timer. That updater builds without root into `~/.local/bin`, preserving the
configuration in `~/.local/src/twmx/config.h`. The package supplies the C
compiler, make, pkgconf and curl needed for those builds. The X11 startup
script prefers the user's build, falling back to the packaged binary.
Failed builds leave the previous binary in place; updates never restart
the running desktop. Run `/usr/bin/twmx-update` for a manual check, or
`systemctl --user mask --now twmx-update.timer` to disable the timer.
Re-enable it with `systemctl --user unmask twmx-update.timer` followed by
`systemctl --user start twmx-update.timer`. Logs are available through
`journalctl --user -u twmx-update.service`.

`configs/` is a home directory skeleton (`.xinitrc`, `.Xresources`,
`.config/...`) that the installer puts in `/etc/skel`, so every new user
gets it. Existing users copy it: `cp -rn /etc/skel/. ~/`.

Window managers have no display manager. Instead the installer appends to
`/etc/skel/.bash_profile` (so the new user's `~/.bash_profile`) a few lines
that start the desktop when you log in on tty1: `exec startx` for twmx and
i3, `exec sway` or `exec start-hyprland` for those. Other ttys stay plain
consoles. Delete the lines to boot to the console. Running `twmx` by hand on
a console fails with "cannot open display": it needs an X server, which
`startx` starts.

The X11 keyboard layout is separate from the console's:
`sudo localectl set-x11-keymap de`.

Sway is still available as the `sway` profile (Wayland, with foot, fuzzel and
mako; its configs are in the same skeleton).

## Modifying the distribution

**Add a package to the live ISO**: add its name to
`archiso/kiln/packages.x86_64`, then `make test` (checks it exists) and
`make iso`.

**Add a file to the live ISO**: put it under `archiso/kiln/airootfs/` at its
target path. Executables also need an entry in `file_permissions` in
`profiledef.sh`.

**Add a package to an installation profile**: edit `profiles/*.toml`, or on
an installed system copy a profile to `~/.config/kiln/profiles/` and edit it;
the user copy wins.

**Change the window manager**: write a profile with the packages (for
example `river` and its tools), apply it, and remove the old one:

```sh
kiln profile create river && $EDITOR ~/.config/kiln/profiles/river.toml
sudo kiln apply river
sudo kiln remove twmx --purge
```

To offer it in the installer, add a profile in `profiles/` and an entry in
`DESKTOPS` at the top of `kiln-install`.

**Add a package Kiln builds itself**: create `packages/<name>/PKGBUILD`;
`make iso` builds it into `[kiln]`. List it in a profile like any package.

**Branding**: see `branding/README.md` for where each piece lives.

## CLI source and update channel

`packages/kiln` pins the public `kilnlinux/kiln-package-manager` Git submodule.
Its PKGBUILD packages `/usr/bin/kiln`; tag workflows publish stable x86_64 Arch
packages. The distro builds that same recipe into its local repository, uses
it in the live ISO, and installs kiln plus kiln-updates in the target.

`packages/kiln-updates` supplies the daily system timer and `kiln-update`.
It checks every installed `[kiln]` package against the latest stable release
of the GitHub repository in its package URL. Only stable releases are
installed. HTTPS downloads must match GitHub's asset digest, size, expected package name, architecture and version. A final
version check prevents downgrades after concurrent updates. Pacman owns the
transaction; dependency failures preserve the existing packages.

The build records revision, release tag and timestamp in
`/usr/share/kiln/build.json`. The updater uses it to report newer distro GitHub
releases and main-branch commits. It caches notices in
`/var/lib/kiln/updates.json`; console login reads that cache without network
requests. It does not replace the running distro. The timer is enabled only
in installed Kiln systems, not on the build host or live ISO.
