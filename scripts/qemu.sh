#!/usr/bin/env bash
# Boot Kiln Linux in QEMU.
#   scripts/qemu.sh iso        newest ISO in out/, UEFI, with a blank 20 GiB disk attached
#   scripts/qemu.sh iso-bios   same, legacy BIOS (live only; the installer is UEFI-only)
#   scripts/qemu.sh disk       boot the installed disk, UEFI
# Needs: qemu-system-x86_64 (qemu-desktop or qemu-base), edk2-ovmf.
set -Eeuo pipefail
cd "$(dirname "$0")/.."

Q=build/qemu
DISK=$Q/disk.qcow2
CODE=/usr/share/edk2/x64/OVMF_CODE.4m.fd
VARS_TEMPLATE=/usr/share/edk2/x64/OVMF_VARS.4m.fd

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
command -v qemu-system-x86_64 >/dev/null || die "install qemu: sudo pacman -S qemu-desktop edk2-ovmf"

mkdir -p "$Q"
[[ -f $DISK ]] || qemu-img create -f qcow2 "$DISK" 20G >/dev/null

args=(-m 2G -smp 2 -nic user,model=virtio-net-pci -vga virtio
      -drive "file=$DISK,if=virtio,format=qcow2")
if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    args+=(-enable-kvm -cpu host)
else
    echo "note: /dev/kvm not usable, falling back to slow emulation" >&2
fi

uefi() {
    [[ -f $CODE ]] || die "missing $CODE; install edk2-ovmf"
    # Persistent EFI variables so boot entries written by bootctl survive.
    [[ -f $Q/OVMF_VARS.fd ]] || cp "$VARS_TEMPLATE" "$Q/OVMF_VARS.fd"
    args+=(-drive "if=pflash,format=raw,readonly=on,file=$CODE"
           -drive "if=pflash,format=raw,file=$Q/OVMF_VARS.fd")
}

iso() {
    local f
    f=$(ls -t out/kilnlinux-*.iso 2>/dev/null | head -n1) || true
    [[ -n $f ]] || die "no ISO in out/; run: make iso"
    args+=(-cdrom "$f" -boot order=d)
}

case ${1:-iso} in
    iso) uefi; iso ;;
    iso-bios) iso ;;
    disk) uefi ;;
    *) die "usage: $0 iso|iso-bios|disk" ;;
esac
exec qemu-system-x86_64 "${args[@]}"
