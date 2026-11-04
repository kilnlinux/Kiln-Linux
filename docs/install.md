# Building, testing in QEMU, installing

## Build the ISO

On Arch Linux:

```sh
sudo pacman -S --needed archiso rust base-devel git
make test
make iso
```

The ISO is `out/kilnlinux-YYYY.MM.DD-x86_64.iso`. No root needed (see
"Rootless builds" in architecture.md); your user needs an `/etc/subuid`
entry, which `useradd` creates by default. Running `sudo make iso` also
works but builds kiln as root.

A failed build leaves `build/work`; the next `make iso` deletes it and starts
fresh. `make clean` removes everything generated.

## Run in QEMU

```sh
sudo pacman -S --needed qemu-desktop edk2-ovmf
make run          # ISO, UEFI, blank 20 GiB disk at build/qemu/disk.qcow2
make run-bios     # ISO, legacy BIOS
make run-disk     # boot the installed disk
make run-disk-bios  # boot the installed disk, legacy BIOS
```

KVM is used when `/dev/kvm` is accessible. To start over with a blank disk:
`rm -r build/qemu`.

The twmx desktop runs on QEMU's default VGA. For the sway profile, QEMU's
virtio GPU may need software rendering: `WLR_RENDERER=pixman sway`.

## Write to a USB stick

The ISO is hybrid. Replace `/dev/sdX` with the stick; **everything on it is
lost**:

```sh
lsblk                                   # identify the stick
sudo dd if=out/kilnlinux-*.iso of=/dev/sdX bs=4M conv=fsync oflag=direct status=progress
```

## Install

Boot the ISO in UEFI or BIOS mode (on BIOS, choose GRUB or Limine), then:

```sh
iwctl                 # Wi-Fi only; Ethernet is automatic
kiln-install
```

The main menu lists every setting with its current value. Pick items in any
order (arrow keys, Enter), then Install. Required choices are marked in the
menu; the bottom line explains the selected item. Tab switches buttons and
Escape goes back. Exit asks before discarding menu choices:

| Item | What it sets |
|---|---|
| Keyboard | console keymap |
| Network | shows whether you're online; opens `iwctl` for Wi-Fi |
| Hostname, Locale, Timezone | as named |
| Root | locked (default; use sudo) or a password |
| User account | your login, in `wheel`, with sudo |
| Desktop | twmx (default), i3, Sway, Hyprland, XFCE, KDE Plasma, GNOME, or none |
| Extras | PipeWire audio, developer tools |
| Disk | erase a whole disk (1 GiB EFI partition + root), or partition with cfdisk and pick the EFI and root partitions; ext4 or btrfs; optional LUKS2 encryption of root (passphrase at every boot) |
| Boot loader | systemd-boot (default on UEFI, UEFI only), GRUB (default on BIOS) or Limine |
| Review | all settings and planned disk changes, without starting installation |
| Log | full scrollable output from the last installation attempt |
| Help | navigation, defaults and disk safety |

Install checks everything first, shows a summary, and asks you to type the
disk name before erasing it. Manual installs require the root partition name
before formatting; the summary also identifies whether /boot will be formatted.
Changes explicitly saved in cfdisk take effect immediately.

Unattended installs: `kiln-install --config FILE`, where FILE sets the
variables listed at the top of the script, for example:

```sh
DISK=/dev/vda SCHEME=auto FS=ext4 DESKTOP=twmx EXTRAS=(audio)
USER_NAME=me USER_PW='change me' TIMEZONE=Europe/Berlin
ENCRYPT=yes LUKS_PW='disk passphrase'   # optional
BOOTLOADER=limine                       # optional: systemd-boot, grub, limine
```

A locked root means systemd's emergency shell can't log in; boot with
`init=/bin/bash` on the kernel command line (press `e` in the boot menu) to
recover, or set a root password under Root.

Installation output labels each of the eight stages. If anything fails,
the installer opens the full scrollable log and writes everything to `/tmp/kiln-install.log`. Copy that log off before rebooting
(the live system lives in RAM).

## After installing

```sh
nmtui                 # connect to Wi-Fi
sudo pacman -Syu      # update
startx                # twmx or i3, if not started on login (twmx: Super+Return opens a terminal)
sudo localectl set-x11-keymap de   # X11 keyboard layout, if not US
sudo kiln apply audio # add PipeWire later
```
