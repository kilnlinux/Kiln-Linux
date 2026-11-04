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
xsetroot -solid '#@bg@' -cursor_name left_ptr
dunst &
# Prefer the user build installed by twmx-update.
export PATH="$HOME/.local/bin:$PATH"
wm=twmx
# twmx has no bar of its own; i3 draws i3bar itself. polybar checks the WM's
# EWMH support once, at startup, so wait (up to 5 s) for twmx to announce it.
if [ "$wm" = twmx ]; then
    (for _ in $(seq 50); do
        xprop -root _NET_SUPPORTING_WM_CHECK | grep -q window && break
        sleep 0.1
    done
    exec polybar kiln) &
fi
exec "$wm"
