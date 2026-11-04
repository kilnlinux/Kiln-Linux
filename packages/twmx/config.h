/* twmx configuration for Kiln Linux, built into the twmx package.
 * Based on twmx config.def.h at the commit pinned in PKGBUILD; differences:
 * Kiln Graphite colors (themes/graphite), dmenu themed to match, and keys for
 * locking, screenshots and Super+Shift+Space floating, as in Kiln's other WMs. */

/* appearance */
static const unsigned int borderpx   = 2;          /* window border width */
static const unsigned int gappx      = 6;          /* gap between windows and screen edges */
static const char normbordercolor[]  = "#34322f";
static const char selbordercolor[]   = "#a4471f";  /* kiln brick */

/* behaviour */
static const int focusfollowsmouse  = 1;   /* 1: focus window under pointer, 0: click to focus */

/* workspaces: one entry per workspace; the count is the number of workspaces */
static const char *wsnames[] = { "1", "2", "3", "4", "5", "6", "7", "8", "9" };

/* tiling */
static const float mfact            = 0.55; /* master area size [0.05..0.95] */
static const int nmaster            = 1;    /* number of windows in master area */
static const Layout layouts[]       = { tile, monocle, floating };
static const int defaultlayout      = 0;    /* index into layouts[]; -1 in setlayout toggles */

/* window rules: substring match on WM_CLASS; ws -1 means current workspace */
static const Rule rules[] = {
	/* class      instance    isfloating  ws */
	{ "Gimp",     NULL,       1,          -1 },
};

/* commands */
static const char *termcmd[]     = { "xterm", NULL };
static const char *launchercmd[] = { "dmenu_run", "-fn", "DejaVu Sans Mono:size=10",
	"-nb", "#242322", "-nf", "#ededed", "-sb", "#a4471f", "-sf", "#ededed", NULL };
static const char *lockcmd[]     = { "i3lock", "-n", "-c", "1a1a1a", NULL };
/* Screenshots to ~/Pictures/Screenshots; region selection with the mouse. */
#define SHOT(FLAGS) { "/bin/sh", "-c", "d=$HOME/Pictures/Screenshots; mkdir -p \"$d\" && " \
	"maim " FLAGS " \"$d/$(date +%Y-%m-%d_%H-%M-%S).png\"", NULL }
static const char *shotcmd[]     = SHOT("");
static const char *shotselcmd[]  = SHOT("-s");

#define MODKEY Mod4Mask   /* Super */
#define WSKEYS(KEY, WS) \
	{ MODKEY,           KEY, view,     { .i = WS } }, \
	{ MODKEY|ShiftMask, KEY, sendtows, { .i = WS } },

static const Key keys[] = {
	/* modifier         key           function          argument */
	{ MODKEY,           XK_Return,    spawn,            { .v = termcmd } },
	{ MODKEY,           XK_d,         spawn,            { .v = launchercmd } },
	{ MODKEY,           XK_q,         killclient,       { 0 } },
	{ MODKEY,           XK_j,         focusstack,       { .i = +1 } },
	{ MODKEY,           XK_k,         focusstack,       { .i = -1 } },
	{ MODKEY|ShiftMask, XK_j,         movestack,        { .i = +1 } },
	{ MODKEY|ShiftMask, XK_k,         movestack,        { .i = -1 } },
	{ MODKEY|ShiftMask, XK_Return,    zoom,             { 0 } },
	{ MODKEY,           XK_i,         incnmaster,       { .i = +1 } },
	{ MODKEY,           XK_o,         incnmaster,       { .i = -1 } },
	{ MODKEY,           XK_h,         setmfact,         { .f = -0.05 } },
	{ MODKEY,           XK_l,         setmfact,         { .f = +0.05 } },
	{ MODKEY,           XK_t,         setlayout,        { .i = 0 } },
	{ MODKEY,           XK_m,         setlayout,        { .i = 1 } },
	{ MODKEY|ShiftMask, XK_f,         setlayout,        { .i = 2 } },
	{ MODKEY,           XK_space,     togglefloating,   { 0 } },
	{ MODKEY|ShiftMask, XK_space,     togglefloating,   { 0 } },
	{ MODKEY,           XK_Escape,    spawn,            { .v = lockcmd } },
	{ 0,                XK_Print,     spawn,            { .v = shotcmd } },
	{ ShiftMask,        XK_Print,     spawn,            { .v = shotselcmd } },
	{ MODKEY,           XK_f,         togglefullscreen, { 0 } },
	{ MODKEY,           XK_Tab,       viewprev,         { 0 } },
	{ MODKEY,           XK_comma,     focusmon,         { .i = -1 } },
	{ MODKEY,           XK_period,    focusmon,         { .i = +1 } },
	{ MODKEY|ShiftMask, XK_comma,     sendmon,          { .i = -1 } },
	{ MODKEY|ShiftMask, XK_period,    sendmon,          { .i = +1 } },
	WSKEYS(XK_1, 0) WSKEYS(XK_2, 1) WSKEYS(XK_3, 2)
	WSKEYS(XK_4, 3) WSKEYS(XK_5, 4) WSKEYS(XK_6, 5)
	WSKEYS(XK_7, 6) WSKEYS(XK_8, 7) WSKEYS(XK_9, 8)
	{ MODKEY|ShiftMask, XK_q,         quit,             { 0 } },
};

/* mouse bindings on client windows (TinyWM's original move/resize) */
static const Button buttons[] = {
	{ MODKEY, Button1, mousedrag,      { .i = 0 } },  /* move */
	{ MODKEY, Button2, togglefloating, { 0 } },
	{ MODKEY, Button3, mousedrag,      { .i = 1 } },  /* resize */
};
