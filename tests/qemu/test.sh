#!/bin/bash
# Fetched by the live ISO from script= on the boot command line (see run.sh).
# Runs in the live ISO (via script= on the kernel command line). Output to serial.
exec >/dev/ttyS0 2>&1
echo KILNTEST-START
curl -fsS http://10.0.2.2:8000/install.cfg -o /root/install.cfg
kiln-install --config /root/install.cfg
rc=$?
if ((rc == 0)); then
    # Auto partitioning puts root last (after the BIOS boot partition on BIOS).
    root=$(lsblk -lnpo NAME,TYPE /dev/vda | awk '$2 == "part" { p = $1 } END { print p }')
    if [[ $(lsblk -no FSTYPE "$root") == crypto_LUKS ]]; then
        echo -n kilntest-luks | cryptsetup open "$root" e2eroot --key-file=- && root=/dev/mapper/e2eroot
    fi
    if mount "$root" /mnt; then
        arch-chroot /mnt pacman -Qo /usr/bin/kiln &&
            arch-chroot /mnt pacman -Q kiln-updates &&
            arch-chroot /mnt systemctl is-enabled kiln-update.timer &&
            arch-chroot /mnt kiln-update --check &&
            # filesystem owns os-release; its upgrade must not bring back Arch's (pacman reinstall counts as Upgrade)
            arch-chroot /mnt pacman -S --noconfirm filesystem &&
            grep -q '^ID=kiln' /mnt/usr/lib/os-release &&
            arch-chroot /mnt gpasswd -a kilntest uucp  # test only: lets the boot check write to /dev/ttyS0
        rc=$?
        umount /mnt || rc=1
        [[ ! -e /dev/mapper/e2eroot ]] || cryptsetup close e2eroot
    else
        rc=1
    fi
fi
echo "KILNTEST-RC=$rc"
