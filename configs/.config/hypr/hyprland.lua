-- Kiln Linux Hyprland config (Lua, Hyprland 0.57+). Reference: https://wiki.hypr.land/Configuring/
-- Installed to ~/.config/hypr/hyprland.lua for new users (from /etc/skel). Used by the hyprland profile.
-- Keys match Kiln's sway and i3 configs. Kiln Graphite (themes/graphite): no animations, blur,
-- shadows or rounding; the look comes from spacing, borders and one accent.

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })

local mod      = "SUPER"
local terminal = "foot"
local menu     = "fuzzel"
local lock     = "swaylock -f -c @bg@"
local shot     = 'd=$HOME/Pictures/Screenshots; mkdir -p "$d" && grim '
local stamp    = ' "$d/$(date +%Y-%m-%d_%H-%M-%S).png"'

hl.on("hyprland.start", function()
    hl.exec_cmd("waybar")
    hl.exec_cmd("mako")
end)

hl.config({
    general = {
        border_size = @border@,
        gaps_in     = 3,
        gaps_out    = @gap@,
        col = {
            active_border   = "rgb(@accent@)",
            inactive_border = "rgb(@line@)",
        },
        layout = "dwindle",
    },
    decoration = {
        rounding = 0,
        shadow   = { enabled = false },
        blur     = { enabled = false },
    },
    animations = { enabled = false },
    misc = {
        disable_hyprland_logo    = true,
        disable_splash_rendering = true,
        force_default_wallpaper  = 0,
        background_color         = "rgb(@bg@)",
    },
    input = {
        touchpad = { tap_to_click = true, natural_scroll = true },
    },
})

-- Basics
hl.bind(mod .. " + Return", hl.dsp.exec_cmd(terminal))
hl.bind(mod .. " + D", hl.dsp.exec_cmd(menu))
hl.bind(mod .. " + Q", hl.dsp.window.close())
hl.bind(mod .. " + Escape", hl.dsp.exec_cmd(lock))
hl.bind(mod .. " + SHIFT + E", hl.dsp.exit())
hl.bind("Print", hl.dsp.exec_cmd(shot .. stamp))
hl.bind("SHIFT + Print", hl.dsp.exec_cmd(shot .. '-g "$(slurp)"' .. stamp))

-- Focus and move
for key, dir in pairs({ H = "left", J = "down", K = "up", L = "right",
                        left = "left", down = "down", up = "up", right = "right" }) do
    hl.bind(mod .. " + " .. key, hl.dsp.focus({ direction = dir }))
    hl.bind(mod .. " + SHIFT + " .. key, hl.dsp.window.move({ direction = dir }))
end

-- Workspaces
for i = 1, 10 do
    local key = i % 10 -- 10 is key 0
    hl.bind(mod .. " + " .. key, hl.dsp.focus({ workspace = i }))
    hl.bind(mod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end

-- Layout
hl.bind(mod .. " + F", hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }))
hl.bind(mod .. " + SHIFT + Space", hl.dsp.window.float({ action = "toggle" }))
hl.bind(mod .. " + E", hl.dsp.layout("togglesplit"))
hl.bind(mod .. " + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind(mod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Volume keys. Work once the audio profile is applied (wpctl is PipeWire's).
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { locked = true, repeating = true })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true })
