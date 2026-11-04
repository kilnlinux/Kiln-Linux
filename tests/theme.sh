#!/usr/bin/env bash
# Render configs/ with themes/graphite into a scratch copy: every @name@ must
# resolve, and twmx's compiled-in colors must be Graphite colors.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp -rT configs "$tmp"
scripts/render-theme.sh themes/graphite "$tmp"
grep -q '^XTerm\*background: *#1a1a1a$' "$tmp/.Xresources"
grep -q 'height = 22$' "$tmp/.config/polybar/config.ini"
# twmx's config.h is compiled into the package, so it holds literal colors.
palette=$(grep -oE '^[a-z0-9_]+=[0-9a-f]{6}' themes/graphite | cut -d= -f2)
for c in $(grep -oE '#?[0-9a-f]{6}\b' packages/twmx/config.h | tr -d '#'); do
    grep -qx "$c" <<<"$palette" || { echo "packages/twmx/config.h: $c is not in themes/graphite"; exit 1; }
done
