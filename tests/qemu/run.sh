#!/usr/bin/env bash
# End-to-end test in QEMU (KVM):
#  1. boot the newest ISO, add script=http://10.0.2.2:8000/test.sh to the boot
#     entry with simulated keypresses; the live system fetches and runs it,
#     which runs `kiln-install --config install.cfg` on a blank virtio disk
#  2. boot the installed disk and screenshot it; desktops started from tty1
#     get logged in, and twmx also opens xterm and runs kiln list
# Environment: DESKTOP (twmx), FIRMWARE (uefi or bios), BOOTLOADER (systemd-boot
# on UEFI, grub on BIOS), FS (ext4 or btrfs), ENCRYPT (no or yes), KERNEL (linux).
# Screenshots and serial logs land in build/e2e/<desktop>-<firmware>-<bootloader>,
# plus -<fs>, -luks and -<kernel> when not the default. Needs qemu and edk2-ovmf.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
here=tests/qemu
DESKTOP=${DESKTOP:-twmx} FIRMWARE=${FIRMWARE:-uefi}
[[ $FIRMWARE == uefi ]] && default_loader=systemd-boot || default_loader=grub
BOOTLOADER=${BOOTLOADER:-$default_loader}
FS=${FS:-ext4} ENCRYPT=${ENCRYPT:-no} KERNEL=${KERNEL:-linux}
name=$DESKTOP-$FIRMWARE-$BOOTLOADER
[[ $FS == ext4 ]] || name+=-$FS
[[ $ENCRYPT == no ]] || name+=-luks
[[ $KERNEL == linux ]] || name+=-$KERNEL
D=$PWD/build/e2e/$name
iso=$(ls -t out/kilnlinux-*.iso | head -n1)
rm -rf "$D" && mkdir -p "$D"
qemu-img create -f qcow2 "$D/disk.qcow2" 20G >/dev/null
cp /usr/share/edk2/x64/OVMF_VARS.4m.fd "$D/vars-disk.fd"
cp "$here/test.sh" "$D/"
{
    cat "$here/install.cfg"
    printf 'DESKTOP=%s\nBOOTLOADER=%s\nFS=%s\nENCRYPT=%s\nKERNEL=(%s)\n' "$DESKTOP" "$BOOTLOADER" "$FS" "$ENCRYPT" "$KERNEL"
    [[ $ENCRYPT == no ]] || echo LUKS_PW=kilntest-luks
} >"$D/install.cfg"

python3 -m http.server 8000 --bind 127.0.0.1 --directory "$D" >/dev/null 2>&1 &
http=$!
trap 'kill $http 2>/dev/null' EXIT
python3 "$here/e2e.py" "$D" "$iso" install "$FIRMWARE" "$DESKTOP" "$ENCRYPT"
python3 "$here/e2e.py" "$D" none boot "$FIRMWARE" "$DESKTOP" "$ENCRYPT"
echo "screenshots: $D/*.png"
