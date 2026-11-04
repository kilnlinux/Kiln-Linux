# Contributing

1. `make test` must pass. It runs kiln's unit and integration tests, clippy
   with warnings as errors, `bash -n` (and shellcheck when installed) on the
   scripts, and checks every package name in the profiles and ISO list
   against the repositories.
2. Changes to the ISO or installer: build with `make iso`, then boot and
   install in QEMU (`make run`, `make run-disk`). Say in the pull request
   what you tested and on which firmware (UEFI/BIOS).
3. Keep it small. A new package or service needs a reason in the pull
   request. Prefer a profile users can opt into over a default.
4. Never make kiln modify pacman's database, run `pacman -Sy`, or remove a
   package kiln did not install.

Code style: `cargo fmt` for Rust; bash with `set -Eeuo pipefail`, quoted
expansions, and argument arrays rather than strings.
