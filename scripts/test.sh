#!/usr/bin/env bash
# Fast checks that need no root and no VM. Booting and installing are
# tested by hand in QEMU: see docs/testing.md.
set -Eeuo pipefail
cd "$(dirname "$0")/.."

pass=0 fail=0
ok() { printf '\033[32mok\033[0m   %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '\033[31mFAIL\033[0m %s\n' "$1"; fail=$((fail + 1)); }
t() { local name=$1; shift; if "$@" >/tmp/kiln-test.$$ 2>&1; then ok "$name"; else bad "$name"; sed 's/^/     /' /tmp/kiln-test.$$; fi; }

t "installer: failure handling" python3 tests/installer.py
t "theme: graphite fills every @name@ in configs" tests/theme.sh
t "twmx: user updater" python3 tests/twmx-update.py

t "kiln: cargo test (unit + integration)" cargo test --quiet --manifest-path packages/kiln/Cargo.toml
t "kiln: cargo clippy, no warnings" cargo clippy --quiet --manifest-path packages/kiln/Cargo.toml -- -D warnings

shells=(packages/kiln-install/kiln-install scripts/*.sh archiso/kiln/profiledef.sh packages/twmx/PKGBUILD packages/twmx/twmx-update-kiln)
for f in "${shells[@]}"; do t "bash -n $f" bash -n "$f"; done
if command -v shellcheck >/dev/null; then
    t "shellcheck" shellcheck -S warning "${shells[@]}"
else
    echo "skip shellcheck (not installed)"
fi

# Every package name must exist in the sync databases of this machine.
names() { grep -hoE '^\s*"[^"]+"' "$@" | tr -d ' "'; }
# Packages Kiln builds itself (packages/*/PKGBUILD) are in [kiln], not in Arch's repos.
own=" $(sed -n 's/^pkgname=//p' packages/*/PKGBUILD | tr '\n' ' ') "
check_pkgs() {
    local p missing=0
    for p in "$@"; do
        [[ $own == *" $p "* ]] && continue
        pacman -Si -- "$p" >/dev/null 2>&1 || { echo "not in repos: $p"; missing=1; }
    done
    return $missing
}
# shellcheck disable=SC2046
t "profiles: all packages exist in repos" check_pkgs $(names profiles/*.toml)
# shellcheck disable=SC2046
t "ISO: all packages exist in repos" check_pkgs $(grep -vE '^\s*(#|$)' archiso/kiln/packages.x86_64)

rm -f /tmp/kiln-test.$$
printf '\n%d passed, %d failed\n' "$pass" "$fail"
((fail == 0))
