#!/usr/bin/env bash
# End-to-end test in QEMU (UEFI, KVM):
#  1. boot the newest ISO, add script=http://10.0.2.2:8000/test.sh to the boot
#     entry with simulated keypresses; the live system fetches and runs it,
#     which runs `kiln-install --config install.cfg` on a blank virtio disk
#  2. boot the installed disk, log in on tty1 (twmx should start), open xterm,
#     run kiln list
# Screenshots and serial logs land in build/e2e/. Needs qemu and edk2-ovmf.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
here=tests/qemu
D=$PWD/build/e2e
iso=$(ls -t out/kilnlinux-*.iso | head -n1)
rm -rf "$D" && mkdir -p "$D"
qemu-img create -f qcow2 "$D/disk.qcow2" 20G >/dev/null
cp /usr/share/edk2/x64/OVMF_VARS.4m.fd "$D/vars-disk.fd"

python3 -m http.server 8000 --bind 127.0.0.1 --directory "$here" >/dev/null 2>&1 &
http=$!
trap 'kill $http 2>/dev/null' EXIT
python3 "$here/e2e.py" "$D" "$iso" install
python3 "$here/e2e.py" "$D" none boot
echo "screenshots: $D/*.png"
