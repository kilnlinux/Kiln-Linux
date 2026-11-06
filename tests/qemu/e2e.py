"""End-to-end test: install Kiln Linux in QEMU, then boot it. Run via tests/qemu/run.sh."""
import sys, time; sys.path.insert(0, __import__('os').path.dirname(__file__)); from vm import VM
d, iso, phase, firmware, desktop, encrypt = sys.argv[1:7]
base = ['-enable-kvm','-cpu','host','-m','3G','-smp','4','-nic','user,model=virtio-net-pci','-vga','std',
        '-drive',f'file={d}/disk.qcow2,if=virtio,format=qcow2']
if firmware == 'uefi':
    base += ['-drive','if=pflash,format=raw,readonly=on,file=/usr/share/edk2/x64/OVMF_CODE.4m.fd',
             '-drive',f'if=pflash,format=raw,file={d}/vars-disk.fd']
if phase == 'install':
    v = VM(base + ['-cdrom', iso, '-boot', 'order=d'], d, 'serial-e2e.log')
    time.sleep(6); v.shot('e2e-menu.png')
    if firmware == 'uefi':   # systemd-boot: e edits the entry, End goes to the end of the line
        v.hmp('sendkey e'); time.sleep(1); v.hmp('sendkey end')
    else:                    # syslinux: Tab edits the entry's command line, cursor at the end
        v.hmp('sendkey tab'); time.sleep(1)
    v.keys(' script=http://10.0.2.2:8000/test.sh'); v.shot('e2e-edit.png'); v.hmp('sendkey ret')
    v.expect('KILNTEST-START', 240)
    m = v.expect(r'KILNTEST-RC=(\d+)', 3000)
    print('INSTALL RC', m.group(1)); v.shot('e2e-done.png')
    v.hmp('system_powerdown'); time.sleep(10); v.kill()
    if m.group(1) != '0': sys.exit('install failed; see serial-e2e.log')
else:
    v = VM(base + ['-boot', 'order=c'], d, 'serial-boot.log')
    time.sleep(4); v.shot('boot-menu.png')
    if encrypt == 'yes':   # sd-encrypt asks on the console once the initramfs is up
        time.sleep(16); v.shot('boot-luks.png'); v.keys('kilntest-luks\n')
    time.sleep(56); v.shot('boot-login.png')
    if desktop in ('twmx', 'i3', 'sway', 'hyprland'):  # started by a tty1 login; others show a login manager
        v.keys('kilntest\n'); time.sleep(2); v.keys('kilntest-pw\n')
        time.sleep(15); v.shot('boot-desktop.png')
    if desktop == 'twmx':
        v.hmp('sendkey meta_l-ret'); time.sleep(3)      # Super+Return: xterm
        v.keys('kiln list\n'); time.sleep(4); v.shot('boot-twmx.png')
    v.hmp('system_powerdown'); time.sleep(10); v.kill()
