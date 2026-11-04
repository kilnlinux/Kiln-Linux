# Packages: pacman and kiln

## pacman

pacman is the package manager. Use it as on any Arch system:

```sh
sudo pacman -Syu              # update everything (do this regularly)
sudo pacman -S htop           # install
sudo pacman -Rs htop          # remove, with dependencies nothing else needs
pacman -Ss editor             # search
pacman -Qe                    # explicitly installed packages
```

Always update with `-Syu`, never `-Sy` alone: Arch supports only full
upgrades. The Arch wiki's pacman page applies to Kiln unchanged.

## kiln

kiln keeps **profiles**: named lists of packages in TOML files. It compares a
profile with the system and has pacman install what is missing. It doesn't
replace pacman; everything you install with pacman stays yours.

```sh
kiln profile list                 # profiles kiln can find (* = active)
kiln profile show twmx            # packages and their status
kiln plan developer               # what apply would do; changes nothing
sudo kiln apply developer         # install what's missing, mark active
kiln list                         # active profiles and kiln-installed packages
sudo kiln remove developer        # mark inactive, keep packages
sudo kiln remove developer --purge  # also uninstall what kiln installed for it
kiln doctor                       # check pacman, dependencies, profiles
kiln search sway                  # pacman -Ss
kiln export mine                  # profile from all explicit packages (pacman -Qqe)
kiln export tools git ripgrep     # profile from a chosen list
```

`apply` and `remove` accept `--dry-run` (`-n`) and `--yes` (`-y`, passes
`--noconfirm` to pacman). Without `--yes` they refuse to run without a
terminal, so nothing is confirmed by accident.

### Profiles shipped

| Profile | Contents |
|---|---|
| `core` | networkmanager, sudo, nano, less, man-db |
| `twmx` | twmx, xorg-server, xorg-xinit, xorg-xrdb, xorg-xsetroot, xorg-xrandr, xterm, dmenu, dunst, polybar, i3lock, maim, ttf-dejavu (the default desktop) |
| `i3` | i3-wm, i3status, i3lock, Xorg, xterm, dmenu, dunst, maim |
| `sway` | sway, swaybg, swaylock, foot, fuzzel, mako, grim, slurp |
| `hyprland` | hyprland, xdg-desktop-portal-hyprland, waybar, foot, fuzzel, mako, swaylock, grim, slurp |
| `xfce` | XFCE core components, thunar, LightDM |
| `plasma` | plasma-desktop, SDDM, konsole, dolphin, plasma-nm, kscreen |
| `gnome` | gnome-shell, GDM, control center, console, nautilus |
| `developer` | git, base-devel, gdb |
| `audio` | pipewire, pipewire-pulse, pipewire-alsa, wireplumber |

Profiles stack: the installer applies `core`, then the chosen desktop, then
any extras. Desktops can sit side by side. To switch from twmx to sway:

```sh
sudo kiln apply sway
sudo kiln remove twmx --purge
```

### Writing a profile

`kiln profile create name` writes `~/.config/kiln/profiles/name.toml`:

```toml
[profile]
name = "name"            # must match the file name
description = "What this is for"

[packages]
official = [             # package names from the repositories in pacman.conf
    "git",
    "neovim",
]
```

Rules, checked on every load:

- `name`: lowercase letters, digits, `-`, `_`; equal to the file name.
- package names follow pacman's rules and appear once.
- unknown keys are errors (a typo like `[pakages]` doesn't silently do
  nothing).
- a package not in any repository stops `apply` before anything changes.

`official` means any repository configured in `/etc/pacman.conf`: the Arch
repositories plus `[kiln]`, the small local repository the installer sets up
for packages Kiln builds itself (today only `twmx`).

kiln looks for `<name>.toml` in `~/.config/kiln/profiles`, then
`/etc/kiln/profiles`, then `/usr/share/kiln/profiles`; the first one wins.
Under `sudo`, "~" is the invoking user's home. Any argument with a `/` or a
`.toml` suffix is read as a path.

### What `remove --purge` removes

Only packages that:

1. kiln installed for this profile (it records them at `apply` time;
   packages already present then are never recorded), and
2. no other active profile manages or lists, and
3. are still installed.

pacman then removes them with `-R` and shows its usual confirmation.
Dependencies stay installed so packages needed by other active profiles
are protected. If another package still depends on one of them, pacman refuses the whole
transaction and kiln keeps the profile active.

One case to know: if kiln installed a package for a profile and you later
also started using it directly, kiln still counts it as the profile's. Keep
it by listing it in another profile, or answer "n" at pacman's prompt.

Shared packages remain managed by the remaining profiles, so removing the
last profile can still purge them.

### State

`/var/lib/kiln/state.toml`, human-readable:

```toml
[profiles.twmx]
manifest = "/usr/share/kiln/profiles/twmx.toml"
managed = ["dmenu", "dunst", "ttf-dejavu", "twmx", "xorg-server", "xorg-xinit", "xterm"]
```

The absolute manifest path is saved when applying a profile, including
custom files outside the search directories. Keep that file available:
purge and doctor read its current contents. Older state files without a
path still use the profile search directories.

Deleting this file makes kiln forget active profiles; it never affects
installed packages.

## Updating kiln

Source and stable packages: https://github.com/kilnlinux/kiln-package-manager.
The distro's `packages/kiln` directory is a pinned Git submodule. After cloning,
run `git submodule update --init --recursive` before building or testing.

New Kiln installations use `/usr/bin/kiln`, owned by the kiln pacman package,
and enable `kiln-update.timer`. It checks daily, downloads a newer stable
x86_64 package, verifies its GitHub SHA-256 digest and package metadata, then
installs it through pacman. Build-library minimum versions prevent installation
on an older incompatible system; update Arch packages with `sudo pacman -Syu`
if pacman reports unsatisfied dependencies. State and profiles remain in place.

```sh
kiln-update --check             # current GitHub CLI/distro releases and source
sudo kiln-update --apply        # update the CLI package; report distro changes
kiln-update --status            # cached notices, without network access
sudo systemctl disable --now kiln-update.timer
```

The updater never installs an ISO or runs a distro upgrade. New distro release
and source links are reported separately. Release tags stamped into an ISO
identify its version; builds without a tag compare release publication time
with the ISO build timestamp. Source checks compare the main branch with the
revision recorded at build time.

Old ISOs that copied an unowned `/usr/local/bin/kiln` need migration before
using this updater: install the kiln package and rename the old local binary
so it cannot shadow `/usr/bin/kiln`. New ISOs handle package installation directly.
