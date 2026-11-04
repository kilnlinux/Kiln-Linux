#!/usr/bin/env bash
# render-theme.sh THEME DIR: replace @name@ in every file under DIR with the
# values from THEME (themes/graphite). Fails if any @name@ is left.
set -Eeuo pipefail
theme=$1 dir=$2
[[ -r $theme && -d $dir ]] || { echo "usage: render-theme.sh THEME DIR" >&2; exit 1; }

expr=()
while IFS= read -r line; do
    [[ $line =~ ^([a-z0-9_]+)=(\"([^\"]*)\"|([^[:space:]]*)) ]] || continue
    key=${BASH_REMATCH[1]} val=${BASH_REMATCH[3]}${BASH_REMATCH[4]}
    expr+=(-e "s|@${key}@|${val}|g")
done <"$theme"

grep -rlZ '@[a-z0-9_]*@' "$dir" | xargs -0r sed -i "${expr[@]}"
if left=$(grep -rnoE '@[a-z0-9_]+@' "$dir"); then
    echo "render-theme.sh: unknown names:" >&2
    echo "$left" >&2
    exit 1
fi
