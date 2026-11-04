#!/bin/sh
# Run by `startx`. Kiln Linux default X session: twmx. Edit freely.

# Session setup from installed packages (D-Bus environment and similar).
if [ -d /etc/X11/xinit/xinitrc.d ]; then
    for f in /etc/X11/xinit/xinitrc.d/?*.sh; do
        [ -x "$f" ] && . "$f"
    done
    unset f
fi

[ -f "$HOME/.Xresources" ] && xrdb -merge "$HOME/.Xresources"
xsetroot -solid '#1a1a1a' -cursor_name left_ptr
dunst &
# Prefer the user build installed by twmx-update.
export PATH="$HOME/.local/bin:$PATH"
exec twmx
