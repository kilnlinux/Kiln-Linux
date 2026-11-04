#!/usr/bin/env python3
"""Exercise installer failure handling with no disk or system mutations."""
from pathlib import Path
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
