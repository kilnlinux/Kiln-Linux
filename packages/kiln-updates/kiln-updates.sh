# shellcheck shell=sh
# Show cached distro update notices at interactive console login; no network call.
if [ -t 1 ] && [ -r /var/lib/kiln/updates.json ]; then
    /usr/bin/kiln-update --status
fi
