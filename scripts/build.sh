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

if [[ ! -f packages/kiln/Cargo.toml ]]; then
    die "kiln source is missing; run git submodule update --init --recursive"
fi
say "Checking build dependencies"
missing=()
for c in mkarchiso cargo pacman mksquashfs xorriso unshare makepkg repo-add git fakeroot gcc python3; do
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
    makepkg_args=(--force --cleanbuild --noconfirm)
    # This package only copies files; its kiln runtime dependency is built for the ISO, not installed on the host.
    [[ $dir != packages/kiln-updates ]] || makepkg_args+=(--nodeps)
    (cd "$dir" && BUILDDIR=$ROOT/build/makepkg PKGDEST=$REPO SRCDEST=$ROOT/build/makepkg/src \
        makepkg "${makepkg_args[@]}")
done
repo-add --quiet "$REPO/kiln.db.tar.zst" "$REPO"/*.pkg.tar.zst

say "Staging archiso profile in build/profile"
[[ -d $WORK ]] && as_ns rm -rf -- "$WORK"
rm -rf -- "$PROFILE"
mkdir -p build
cp -a archiso/kiln "$PROFILE"
A=$PROFILE/airootfs
# pacstrap installs the kiln and kiln-updates packages from the local repository.
cat >>"$PROFILE/pacman.conf" <<CONF

[kiln]
SigLevel = Optional TrustAll
Server = file://$REPO
CONF
printf '\nkiln\nkiln-updates\n' >>"$PROFILE/packages.x86_64"
python3 - "$A/usr/share/kiln/build.json" <<'PYMETA'
import datetime, json, pathlib, subprocess, sys
revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
tag = subprocess.run(["git", "describe", "--tags", "--exact-match"], capture_output=True, text=True)
path = pathlib.Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({"revision": revision, "release": tag.stdout.strip() if tag.returncode == 0 else None,
                            "built_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}) + "\n")
PYMETA
install -Dm755 packages/kiln-install/kiln-install "$A/usr/local/bin/kiln-install"
install -d "$A/usr/share/kiln/profiles"
install -m644 profiles/*.toml "$A/usr/share/kiln/profiles/"
# Home directory skeleton; the installer copies it to the new system's /etc/skel.
mkdir -p "$A/usr/share/kiln/skel"
cp -rT configs "$A/usr/share/kiln/skel"
# Configs use @name@ for theme values; fill them in from the default theme.
scripts/render-theme.sh themes/graphite "$A/usr/share/kiln/skel"
# The [kiln] repo; the installer copies it to the new system and adds it to pacman.conf.
# repo-add makes kiln.db/kiln.files symlinks; -L stores real files.
cp -rL "$REPO" "$A/usr/share/kiln/repo"

say "Running mkarchiso"
mkdir -p "$OUT"
mkarchiso -v -r -w "$WORK" -o "$OUT" "$PROFILE"

iso=$(ls -t "$OUT"/kilnlinux-*.iso | head -n1)
say "Built $iso ($(du -h "$iso" | cut -f1))"
say "Boot it: make run   (UEFI)   or   make run-bios"
