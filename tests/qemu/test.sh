#!/bin/bash
# Fetched by the live ISO from script= on the boot command line (see run.sh).
# Runs in the live ISO (via script= on the kernel command line). Output to serial.
exec >/dev/ttyS0 2>&1
echo KILNTEST-START
curl -fsS http://10.0.2.2:8000/install.cfg -o /root/install.cfg
kiln-install --config /root/install.cfg
rc=$?
if ((rc == 0)); then
    if mount /dev/vda2 /mnt; then
        arch-chroot /mnt pacman -Qo /usr/bin/kiln &&
            arch-chroot /mnt pacman -Q kiln-updates &&
            arch-chroot /mnt systemctl is-enabled kiln-update.timer &&
            arch-chroot /mnt kiln-update --check
        rc=$?
        umount /mnt || rc=1
    else
        rc=1
    fi
fi
echo "KILNTEST-RC=$rc"
