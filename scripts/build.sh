#!/usr/bin/env bash
# Build the Kiln Linux ISO.
#
# 1. Check build dependencies.
# 2. Build the kiln binary (cargo, release).
# 3. Build Kiln's own pacman packages (packages/*/PKGBUILD, e.g. twmx) into a
#    local repository, build/repo, named [kiln].
# 4. Stage: copy archiso/kiln to build/profile and add kiln, kiln-install,
#    the profiles, the [kiln] repo and the home skeleton into its airootfs.
# 5. Run mkarchiso on the staged copy. The ISO lands in out/.
#
# Runs as a normal user: archiso >= 82 builds rootless through unshare(1)
# with the subordinate IDs in /etc/subuid. Running as root also works.
set -Eeuo pipefail

cd "$(dirname "$0")/.."
ROOT=$PWD
PROFILE=$ROOT/build/profile
WORK=$ROOT/build/work
REPO=$ROOT/build/repo
OUT=$ROOT/out

say() { printf '\033[38;2;164;71;31m::\033[0m %s\n' "$*"; }
die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }
trap 'die "build failed at line $LINENO (see output above)"' ERR

# Files in the work dir are owned by subordinate UIDs when built rootless,
# so delete it inside the same user namespace.
as_ns() { if ((EUID == 0)); then "$@"; else unshare --map-auto --map-root-user -- "$@"; fi; }

say "Checking build dependencies"
missing=()
for c in mkarchiso cargo pacman mksquashfs xorriso unshare makepkg repo-add git fakeroot gcc; do
    command -v "$c" >/dev/null || missing+=("$c")
done
((${#missing[@]} == 0)) || die "missing: ${missing[*]}  (install: sudo pacman -S --needed archiso rust base-devel git)"
if ((EUID != 0)) && ! grep -q "^$(id -un):" /etc/subuid; then
    die "no /etc/subuid entry for $(id -un); rootless mkarchiso needs one (or run as root)"
fi

say "Building kiln"
cargo build --release --locked --manifest-path packages/kiln/Cargo.toml

say "Building the [kiln] package repository"
rm -rf -- "$REPO"
mkdir -p "$REPO" build/makepkg
for pkgbuild in packages/*/PKGBUILD; do
    dir=$(dirname "$pkgbuild")
    say "  makepkg $dir"
    # Not -s: makepkg reports missing build dependencies instead of installing them.
    (cd "$dir" && BUILDDIR=$ROOT/build/makepkg PKGDEST=$REPO SRCDEST=$ROOT/build/makepkg/src \
        makepkg --force --cleanbuild --noconfirm)
done
repo-add --quiet "$REPO/kiln.db.tar.zst" "$REPO"/*.pkg.tar.zst

say "Staging archiso profile in build/profile"
[[ -d $WORK ]] && as_ns rm -rf -- "$WORK"
rm -rf -- "$PROFILE"
mkdir -p build
cp -a archiso/kiln "$PROFILE"
A=$PROFILE/airootfs
install -Dm755 packages/kiln/target/release/kiln "$A/usr/local/bin/kiln"
install -Dm755 packages/kiln-install/kiln-install "$A/usr/local/bin/kiln-install"
install -d "$A/usr/share/kiln/profiles"
install -m644 profiles/*.toml "$A/usr/share/kiln/profiles/"
# Home directory skeleton; the installer copies it to the new system's /etc/skel.
mkdir -p "$A/usr/share/kiln/skel"
cp -rT configs "$A/usr/share/kiln/skel"
# The [kiln] repo; the installer copies it to the new system and adds it to pacman.conf.
# repo-add makes kiln.db/kiln.files symlinks; -L stores real files.
cp -rL "$REPO" "$A/usr/share/kiln/repo"

say "Running mkarchiso"
mkdir -p "$OUT"
mkarchiso -v -r -w "$WORK" -o "$OUT" "$PROFILE"

iso=$(ls -t "$OUT"/kilnlinux-*.iso | head -n1)
say "Built $iso ($(du -h "$iso" | cut -f1))"
say "Boot it: make run   (UEFI)   or   make run-bios"
