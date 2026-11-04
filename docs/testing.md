# Testing

## Automated: `make test`

No root, no VM, under a minute:

- twmx updater wrapper: configuration seeding and preservation, delegation to
  the updated upstream helper, error propagation and root refusal;
- installer failure handling with mocked commands: every failed stage stops
  immediately, without touching disks; download recovery checks bounded retries,
  fallback mirrors, full database refreshes, preserved mirror lists and fatal
  signature errors;
- kiln unit tests (manifest validation, planning rules, CLI parsing, state
  file round trip) and integration tests (the real binary against a fake
  `pacman` on `PATH`: plan buckets, unknown packages, idempotent apply, root
  check, purge planning, export, doctor);
- `cargo clippy -D warnings`;
- `bash -n` on every script, and shellcheck if installed;
- every package name in `profiles/` and `packages.x86_64` exists in the
  repositories.

## Manual: real pacman, no root

archiso's rootless mode makes this possible: `pacstrap -N` installs into a
directory inside a user namespace, and `arch-chroot -N` enters it. The
commands, as run on 2026-11-03:

```sh
R=/tmp/kiln-root; mkdir -p $R
pacstrap -N $R base
unshare --map-auto --map-root-user -- sh -c "
  install -Dm755 packages/kiln/target/release/kiln $R/usr/local/bin/kiln
  mkdir -p $R/usr/share/kiln && cp -r profiles $R/usr/share/kiln/"
arch-chroot -N $R pacman -S --noconfirm foot     # a "manually installed" package
arch-chroot -N $R kiln apply core --yes
arch-chroot -N $R kiln apply desktop --yes
arch-chroot -N $R kiln apply desktop             # second run
arch-chroot -N $R kiln remove desktop --purge --yes
arch-chroot -N $R kiln doctor
```

Results:

- `apply core`, `apply desktop`: pacman installed the missing packages and
  state recorded only those; `foot` (already installed) was not recorded.
- second `apply desktop`: "satisfied, nothing to do", no pacman call.
- `remove desktop --purge`: removed the 6 kiln-installed packages and 59
  dependencies; **`foot` stayed installed**; core stayed active.
- `doctor`: all checks ok.
- Configs, checked with the real tools: `sway -C` (headless backend),
  `foot --check-config`, `fuzzel --check-config`: all pass. twmx with
  Kiln's `config.h` and `.Xresources` checked in Xvfb (screenshot). (`sway -C`
  does fail on a deliberately broken config, so the pass means something.)

## ISO build

`make iso` on 2026-11-03 (archiso 92, rootless): success, no mkinitcpio
errors, `out/kilnlinux-2026.11.03-x86_64.iso`, 1.1 GiB (squashfs 912 MiB).
Inspected without booting (`xorriso`, `unsquashfs`): BIOS and UEFI El Torito
images present, UEFI menu titled "Kiln Linux live medium", `/usr/lib/os-release`
is Kiln's (applied by the pacman hook during the build), root shell is bash,
`kiln`, `kiln-install`, profiles and skel configs are in place.

## QEMU, end to end: `make e2e`

`tests/qemu/run.sh` boots the newest ISO in QEMU (UEFI, OVMF, KVM), edits the
boot entry with simulated keypresses to add `script=http://10.0.2.2:8000/test.sh`,
and the live system runs `kiln-install --config tests/qemu/install.cfg`
(erase `/dev/vda`, ext4, twmx). It then boots the installed disk, logs in,
and takes screenshots into `build/e2e/`.

Run on 2026-11-03:

- ISO boots on UEFI (systemd-boot menu) and BIOS (syslinux menu) to the
  Kiln motd with root auto-login.
- Unattended install: every step ran, all 10 validation checks passed
  (kernel, initramfs, systemd-boot, fallback loader, root UUID in the boot
  entry and fstab, /boot in fstab, user, os-release, `kiln doctor`).
- Installed system: boots through systemd-boot, user login works, fastfetch
  shows the Kiln logo and `OS: Kiln Linux`, `kiln list` shows core and twmx,
  `systemctl --failed` is empty, `startx` starts twmx and Super+Return opens
  the themed xterm.

Earlier, a manual install on a VM caught a real bug: the installer wrote a
boot entry for a fallback initramfs that current Arch no longer builds.
Validation refused to report success; the entry is gone now.

Later, a user installed through the interactive dialog menus on a VM (ext4,
twmx): the install finished, the system booted and login worked. That run
showed kernel messages drawing over the progress box (now suppressed) and
no desktop on login. After the installer gained the tty1 autostart lines, a
reinstall from the rebuilt ISO confirmed that logging in on tty1 starts twmx.

The manual disk path also works: partitioning a VM disk in cfdisk (GPT, 1 GiB
EFI System, the rest Linux filesystem), then picking the EFI and root
partitions in the installer.

## Not yet tested

- [ ] btrfs, a root password
- [ ] LUKS2 root encryption (`ENCRYPT=yes`): install, passphrase prompt at boot
- [ ] desktops other than twmx: i3, sway, Hyprland, XFCE, Plasma, GNOME
      (profiles plan cleanly; packages exist; not installed in a VM)
- [ ] installer failure path under real faults (e.g. pull the network during
      pacstrap); `tests/installer.py` covers each stage failing with mocked commands
- [ ] `sudo pacman -Syu` on the installed system keeps Kiln's os-release
- [ ] real hardware

## Resource use

Measured (pacman's "Installed Size", summed, in the rootless chroot above,
which has no kernel or firmware):

| Set | Size | Packages |
|---|---|---|
| base + core | 731 MiB | 178 |
| base + core + desktop | 1094 MiB | 243 |

An installed system adds `linux` (162 MiB), `linux-firmware` (418 MiB
across its split packages), microcode and initramfs images on the ESP.
Firmware is the biggest single item, and is kept: without it, most Wi-Fi and
GPUs don't work.

Idle RAM, measured once (QEMU, 3 GiB, twmx install, logged in on the TTY,
55 s after boot, before startx): 290 MiB used, as fastfetch reports it.
Boot time is not measured yet. To measure on an installed system, after boot
and login, idle for a minute:

```sh
free -m                          # "used" column
systemd-analyze                  # kernel + userspace boot time
systemd-analyze blame | head     # slowest units
systemctl list-units --type=service --state=running
```

Expected running services on Core: systemd's own (journald, udevd, logind,
timesyncd, enabled by the installer), dbus-broker, NetworkManager, wpa_supplicant (when Wi-Fi is
used), getty. Nothing from Kiln runs in the background: `kiln` only runs
when you call it.
