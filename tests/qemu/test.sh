#!/bin/bash
# Fetched by the live ISO from script= on the boot command line (see run.sh).
# Runs in the live ISO (via script= on the kernel command line). Output to serial.
exec >/dev/ttyS0 2>&1
echo KILNTEST-START
curl -fsS http://10.0.2.2:8000/install.cfg -o /root/install.cfg
kiln-install --config /root/install.cfg
echo "KILNTEST-RC=$?"
