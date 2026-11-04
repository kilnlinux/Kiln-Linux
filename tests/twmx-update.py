#!/usr/bin/env python3
"""Check the user updater wrapper without GitHub or system modifications."""
import os
from pathlib import Path
import subprocess
import tempfile

wrapper = Path("packages/twmx/twmx-update-kiln").read_text()
with tempfile.TemporaryDirectory(prefix="kiln-twmx-update-test-") as temporary:
    root = Path(temporary)
    share = root / "share"
    share.mkdir()
    (share / "config.h").write_text("Kiln config\n")
    (share / "twmx-update").write_text('#!/bin/sh\nprintf "upstream:%s:%s:%s\\n" "$TWMX_PREFIX" "$TWMX_SRC" "$*"\n')
    (share / "twmx-update").chmod(0o755)
    script = root / "wrapper"
    script.write_text(wrapper.replace("/usr/share/twmx", str(share)))
    tools = root / "bin"
    tools.mkdir()
    identity = tools / "id"
    identity.write_text("#!/bin/sh\necho 1000\n")
    identity.chmod(0o755)
    home = root / "home"
    home.mkdir()
    env = dict(os.environ, HOME=str(home), PATH=f"{tools}:{os.environ['PATH']}")

    def run(*args):
        return subprocess.run(["sh", str(script), *args], env=env, capture_output=True, text=True, timeout=10)

    result = run("--force")
    assert result.returncode == 0, result.stderr
    assert f"upstream:{home}/.local:{home}/.local/src/twmx:--force" in result.stdout
    config = home / ".local/src/twmx/config.h"
    assert config.read_text() == "Kiln config\n"
    config.write_text("User config\n")
    updater = home / ".local/bin/twmx-update"
    updater.parent.mkdir(parents=True)
    updater.write_text('#!/bin/sh\necho updated-updater\nexit 7\n')
    updater.chmod(0o755)
    result = run()
    assert result.returncode == 7 and "updated-updater" in result.stdout
    assert config.read_text() == "User config\n"
    identity.write_text("#!/bin/sh\necho 0\n")
    result = run()
    assert result.returncode != 0 and "without sudo" in result.stderr
print("twmx updater: Kiln config seeded, user edits preserved, self-updated helper used, failures propagated, root refused.")
