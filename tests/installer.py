#!/usr/bin/env python3
"""Exercise installer failure handling with no disk or system mutations."""
from pathlib import Path
import os
import subprocess
import tempfile

source = Path("packages/kiln-install/kiln-install").read_text()
functions = source.split("# --- Main ", 1)[0]
stages = [
    "partition_and_mount", "install_base", "install_kiln_files", "configure_system",
    "apply_profiles", "create_user", "install_bootloader", "validate",
]

# Test the same invocation as both entry points: a conditional suppresses errexit.
assert "if do_install" not in source
assert source.count("\n    do_install\n") == 1
assert source.count("\n            do_install\n") == 1

with tempfile.TemporaryDirectory(prefix="kiln-installer-test-") as directory:
    functions = functions.replace("readonly LOG=/tmp/kiln-install.log", f"readonly LOG={directory}/install.log")
    for failed, unattended in [(stage, mode) for stage in [*stages, None] for mode in ("1", "")]:
        mocks = "\n".join(
            f"{stage}() {{ echo STAGE:{stage}; {'false; echo CONTINUED_AFTER_FAILURE' if stage == failed else ':'}; }}"
            for stage in stages
        )
        script = functions + "\n" + mocks + """
mountpoint() { return 1; }
dmesg() { :; }
dialog() { cat; }
sync() { :; }
run() { echo UNMOUNT; }
UNATTENDED=1
do_install
rc=$?
if ((rc == 0)); then echo SUCCESS; else echo FAILURE; fi
exit "$rc"
"""
        script = script.replace("UNATTENDED=1\n", f"UNATTENDED={unattended}\n")
        result = subprocess.run(["bash"], input=script, text=True, capture_output=True, timeout=10)
        if failed:
            assert result.returncode != 0, (failed, result.stdout, result.stderr)
            assert "FAILURE" in result.stdout
            assert "SUCCESS" not in result.stdout
            assert "UNMOUNT" not in result.stdout
            assert "CONTINUED_AFTER_FAILURE" not in result.stdout
            for later in stages[stages.index(failed) + 1:]:
                assert f"STAGE:{later}" not in result.stdout, result.stdout
        else:
            assert result.returncode == 0, (result.stdout, result.stderr)
            assert "UNMOUNT" in result.stdout and "SUCCESS" in result.stdout
print("Installer: eight failure stages stop immediately in both modes; success completes.")

# Exercise the real retry helper; all mirrors and command counters live in /tmp.
with tempfile.TemporaryDirectory(prefix="kiln-download-test-") as directory:
    root = Path(directory)
    for mode, attempts, refreshes, success in [
        ("success", 1, 0, True),
        ("download-once", 2, 1, True),
        ("download-always", 3, 2, False),
        ("signature", 1, 0, False),
        ("mixed-signature", 1, 0, False),
        ("refresh-failure", 1, 1, False),
    ]:
        mirrorlist = root / f"{mode}.mirrorlist"
        original = "# custom mirror\nServer = https://example.invalid/$repo/os/$arch\n"
        mirrorlist.write_text(original)
        commands = root / f"{mode}.commands"
        counters = root / f"{mode}.count"
        script = functions + r'''
sleep() { :; }
arch-chroot() {
    echo "$*" >> "$TEST_COMMANDS"
    if [[ $2 == pacman ]]; then
        if [[ $TEST_MODE == refresh-failure ]]; then
            echo 'error: invalid or corrupted package (PGP signature)'
            return 1
        fi
        return 0
    fi
    local count=0
    [[ ! -f $TEST_COUNT ]] || read -r count < "$TEST_COUNT"
    count=$((count + 1))
    echo "$count" > "$TEST_COUNT"
    case $TEST_MODE in
        success) return 0 ;;
        download-once) ((count > 1)) && return 0 ;;
        signature) echo 'error: invalid or corrupted package (PGP signature)'; return 1 ;;
        mixed-signature)
            echo 'error: failed retrieving file example.pkg.tar.zst : timeout'
            echo 'error: invalid or corrupted package (PGP signature)'
            return 1 ;;
    esac
    echo 'error: failed retrieving file example.pkg.tar.zst : The requested URL returned error: 404'
    return 1
}
set -e
retry_downloads "$TEST_MIRRORS" arch-chroot /mock-target kiln apply desktop --yes
echo COMPLETED
'''
        result = subprocess.run(
            ["bash"], input=script, text=True, capture_output=True, timeout=10,
            env=dict(os.environ, TEST_MODE=mode, TEST_MIRRORS=str(mirrorlist),
                     TEST_COMMANDS=str(commands), TEST_COUNT=str(counters)),
        )
        assert (result.returncode == 0) == success, (mode, result.stdout, result.stderr)
        assert int(counters.read_text()) == attempts, (mode, result.stdout)
        calls = commands.read_text().splitlines()
        assert sum("pacman -Syyu --noconfirm" in line for line in calls) == refreshes, calls
        if refreshes:
            assert Path(str(mirrorlist) + ".kiln-original").read_text() == original
            assert "$repo/os/$arch" in mirrorlist.read_text()
            assert original in mirrorlist.read_text()
            assert "404" in result.stdout
        else:
            assert mirrorlist.read_text() == original
            assert not Path(str(mirrorlist) + ".kiln-original").exists()
        assert ("COMPLETED" in result.stdout) == success
print("Downloads: bounded retry, fallback mirrors, full upgrade, preserved mirror list, fatal signature errors.")

# Check interactive decisions without running dialog or touching any disks.
ui_checks = r'''
set -e
online() { return 0; }
next=user
capture=$(mktemp)
d() { printf '%s\n' "$@" > "$capture"; }
main_menu
 grep -qx 'UserAccount' "$capture"
 grep -qx 'Install' "$capture"
settings_text > "$capture"
 grep -q 'Still needed: UserAccount Disk' "$capture"
USER_NAME=test USER_PW=secret DISK=/dev/test SCHEME=auto
settings_text > "$capture"
 ! grep -q 'Still needed' "$capture"
 grep -q 'ERASE all of /dev/test' "$capture"
 ! grep -q secret "$capture"
rm -f "$capture"
d() { if [[ " $* " == *' --inputbox '* ]]; then printf '%s' "$ANSWER"; fi; }
ANSWER=/dev/test
confirm_disk_changes
ANSWER=wrong
if confirm_disk_changes; then exit 1; fi
SCHEME=manual ROOT=/dev/test2 ESP=/dev/test1 FORMAT_ESP=yes
ANSWER=/dev/test2
confirm_disk_changes
ANSWER=/dev/test
if confirm_disk_changes; then exit 1; fi
ROOT_PW=original
d() { return 255; }
ask_password() { echo 'Unexpected password prompt after Escape' >&2; exit 1; }
# Menu handlers run without errexit; a canceled dialog must preserve the setting.
set +e
ask_root_password
set -e
[[ $ROOT_PW == original ]]
echo 'TUI: required choices, review status, auto/manual disk confirmation and Escape behavior pass.'
'''
result = subprocess.run(["bash"], input=functions + ui_checks, capture_output=True, text=True, timeout=10)
assert result.returncode == 0, (result.stdout, result.stderr)
print(result.stdout.strip())
