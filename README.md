# StickUI

A borderless, always-on-top controller layout overlay for arcade sticks and emulators.
Displays a visual reference of button mappings for any system or game, positioned to match your physical cabinet layout.
**Auto-reloads when any config file is saved.**

```bash
python -m stickui --system snes
python -m stickui --system mame --game sf2
python -m stickui --system snes --stick myStick --width 700 --height 300
```

---

## Features

- **Borderless translucent overlay** — stays on top of your emulator
- **Auto-reload** — edit any config file and the UI updates instantly, no restart needed
- **Stick layout config** — define exact pixel positions for every button and direction arrow to match your physical cabinet
- **Three-tier label system** — stick defines positions, system defines default labels, game overrides specific labels
- **Cardinal direction arrows** — ▲ ◀ ▼ ▶ with custom labels when a game remaps directions
- **Logo overlay** — floating PNG, does not affect button layout. Falls back from game → system automatically
- **Background image** — PNG or JPG/JPEG, cover-scaled to fill the window at any size with a subtle vignette
- **Settings dialog** — invisible button in the bottom-right corner (or right-click → Settings) opens a dialog to adjust position, size, opacity and auto-hide. Changes are saved to `config.toml` immediately
- **Draggable** — left-click drag to reposition
- **Right-click menu** — Settings, Copy Position, Reload Now, Quit
- **ESC** to close

---

## Installation

```bash
pip install -r requirements.txt
```

Python 3.11+ recommended (ships with `tomllib`). For Python 3.9/3.10:

```bash
pip install -r requirements.txt tomli
```

Optional — install `tomli-w` for cleaner config file writes from the settings dialog:

```bash
pip install tomli-w
```

Without it, StickUI falls back to a line-by-line patcher that works fine for standard config files.

---

## Running

```bash
# From the repo root:
python -m stickui --system snes
python -m stickui --system mame --game sf2
python -m stickui --system snes --stick myStick --xpos 50 --ypos 900 --width 620 --height 280
```

### CLI Flags

| Flag | Description |
|---|---|
| `--system` | Emulator id: `mame`, `snes`, `nes`, `genesis`, … **(required)** |
| `--game` | ROM name without extension: `sf2`, `smw`, … |
| `--stick` | Stick config name in `sticks/` folder (default: from system.toml or `default`) |
| `--xpos` | Window X position (overrides config.toml) |
| `--ypos` | Window Y position (overrides config.toml) |
| `--width` | Window width in pixels |
| `--height` | Window height in pixels |

---

## Directory Structure

```
stickUI/                          ← run from here
├── config.toml                   ← global settings
├── sticks/
│   └── default.toml              ← stick hardware layout (button positions)
├── systems/
│   ├── mame/
│   │   ├── system.toml           ← MAME default labels + display settings
│   │   ├── mame.png              ← system logo fallback
│   │   ├── background.jpg        ← system background (png or jpg)
│   │   ├── sf2.toml              ← per-game label overrides
│   │   └── sf2.png               ← game logo (optional)
│   └── snes/
│       ├── system.toml
│       ├── snes.png
│       └── background.jpg
└── stickui/                      ← Python package
    ├── __main__.py
    ├── core/
    │   ├── config.py
    │   ├── layout.py
    │   ├── mame_parser.py
    │   ├── stick.py
    │   └── watcher.py
    └── ui/
        ├── background.py         ← cover-scaled background renderer
        ├── panel.py
        ├── settings_dialog.py    ← settings UI
        └── window.py
```

---

## Config Reference

### `config.toml` — Global settings

```toml
[general]
xpos   = 100
ypos   = 100
width  = 620
height = 280
opacity = 0.92
auto_hide_seconds = 0   # 0 = never auto-close

[paths]
systems_dir    = './systems'
mame_cfg_dir   = 'd:/mame/cfg'
mame_ctrlr_dir = 'd:/mame/ctrlr'
```

> **Windows paths:** always use forward slashes or single-quoted strings.
> `mame_cfg_dir = 'd:/mame/cfg'` ✓  — `mame_cfg_dir = "d:\mame\cfg"` ✗

---

### `sticks/<n>.toml` — Hardware layout

Defines where every input appears on screen in pixels, relative to the top-left of the window.
Tune `x` / `y` values to match your physical cabinet.

```toml
[stick]
name        = "Default 4+8 Arcade Stick"
description = "Select+Start at top, 4-way stick, 2 rows of 4 buttons"

# Small meta buttons at the top of the panel
[[buttons]]
id   = "select"
x    = 80
y    = 40
size = 34       # optional per-button size override

[[buttons]]
id   = "start"
x    = 140
y    = 40
size = 34

# Directional arrows
[[directions]]
id = "up"
x  = 100
y  = 130

[[directions]]
id = "left"
x  = 60
y  = 165

[[directions]]
id = "right"
x  = 140
y  = 165

[[directions]]
id = "down"
x  = 100
y  = 200

# Action buttons — 2 rows of 4
[[buttons]]
id = "b1"
x  = 300
y  = 140

# ... b2 through b8 ...

[display]
arrow_size   = 34   # default arrow button size in px
button_size  = 52   # default action button diameter in px
```

**Direction ids:** `up`, `down`, `left`, `right`
**Button ids:** `select`, `start`, `b1` – `b8`

To find the right positions: run the app, drag the window into place,
right-click → **Copy Position** to get the window coordinates, then
measure button offsets from the window's top-left corner.

---

### `systems/<s>/system.toml` — System defaults

```toml
[system]
name       = "Super Nintendo"
stick      = "default"        # which stick layout to use
logo       = "snes.png"       # optional — see logo fallback chain below
background = "background.jpg" # optional — png or jpg

[display]
button_color        = "#8b5cf6"
button_label_color  = "#ffffff"
button_border_color = "#a78bfa"
stick_color         = "#1e1b4b"
panel_color         = "#111827"  # gradient fallback if no background image

# Logo display (all optional)
logo_height  = 48       # px — how tall to scale the logo
logo_x       = -1       # px from left; -1 = auto right-align
logo_y       = 8        # px from top
logo_margin  = 12       # margin when auto right-aligning
logo_opacity = 0.9      # 0.0 – 1.0

# Header text
show_title         = true
show_system_name   = true
title_font_size    = 14
subtitle_font_size = 9

[directions]
up    = "Up"
down  = "Down"
left  = "Left"
right = "Right"

[buttons]
select = "Select"
start  = "Start"
b1 = "Y"
b2 = "X"
b3 = "L"
b4 = "R"
b5 = "B"
b6 = "A"
b7 = ""
b8 = ""
```

---

### `systems/<s>/<game>.toml` — Per-game overrides

Only include what differs from the system defaults.

```toml
[game]
name = "Street Fighter II"
logo = "sf2.png"        # optional — falls back to system logo if missing

[display]
button_color = "#dc2626"  # override colours for this game only

[buttons]
b1 = "Light Punch"
b2 = "Med Punch"
b3 = "Heavy Punch"
b4 = "Light Kick"
b5 = "Med Kick"
b6 = "Heavy Kick"

[directions]
up   = "Jump"
down = "Crouch"
```

---

## Settings Dialog

Open via the **invisible button in the bottom-right corner** of the overlay, or right-click → **⚙️ Settings**.

| Control | Description |
|---|---|
| X / Y | Window position on screen. `[−]` and `[+]` buttons step by 10px |
| Width / Height | Window size. Steps by 10px |
| Capture button | Snaps all four fields to the window's current live position and size |
| Opacity slider | 5%–100%. Minimum 5% so the window stays visible and clickable |
| Auto-hide | Enable and set delay in seconds (slider, 1–120s) |
| Apply && Save | Writes changes to `config.toml` and applies them immediately |

---

## Background Images

Backgrounds are cover-scaled using QPainter — the image always fills the full window with no empty borders, regardless of window or image size.

Scaling: `scale = max(window_w / img_w, window_h / img_h)` — the larger ratio wins, image is centred.
A subtle vignette overlay keeps text readable over any background.

**Supported formats:** `.png`, `.jpg`, `.jpeg`

If no background is found, a diagonal gradient from `panel_color` is used instead.

### Background fallback chain

| Priority | Source |
|---|---|
| 1 | `[game] background = "..."` in `<game>.toml` |
| 2 | `<game>_bg.png / .jpg / .jpeg` — implicit game background |
| 3 | `background.png / .jpg / .jpeg` — generic fallback |
| 4 | Same chain at system level |
| 5 | Gradient from `panel_color` |

---

## Logo Fallback Chain

| Priority | Source |
|---|---|
| 1 | `[game] logo = "sf2.png"` in `<game>.toml` |
| 2 | `sf2.png` — same filename as the ROM |
| 3 | `[system] logo = "mame.png"` in `system.toml` |
| 4 | `logo.png` — generic fallback |
| 5 | `mame.png` — system id as filename |

All files are looked up inside the system folder, e.g. `systems/mame/`.

---

## Label Priority (highest → lowest)

| Source | Applies to |
|---|---|
| CLI flags | Window position / size |
| `<game>.toml` `[buttons]` / `[directions]` | Labels |
| MAME `.cfg` XML | Labels (MAME only, fallback when no game toml) |
| `system.toml` `[buttons]` / `[directions]` | Labels |
| `sticks/<n>.toml` | Button positions and sizes |
| `config.toml` | Window defaults, paths |

---

## Auto-Reload

StickUI watches all active config files for changes:

- `config.toml`
- `systems/<s>/system.toml`
- `systems/<s>/<game>.toml`
- `sticks/<n>.toml`

Save any of these and the UI refreshes within 300ms. Window position and size are preserved.
Force a reload at any time via right-click → **🔄 Reload Now**.

---

## Controls

| Action | How |
|---|---|
| Move window | Left-click drag |
| Close | ESC |
| Open settings | Click bottom-right corner, or right-click → Settings |
| Copy window position | Right-click → Copy Position |
| Force reload | Right-click → Reload Now |
| Quit | Right-click → Quit |

---

## Adding a New System

1. Create `systems/<system_id>/`
2. Add `system.toml` (copy from `snes/` and adapt)
3. Optionally add `<system_id>.png` for the logo and `background.jpg`
4. Run: `python -m stickui --system <system_id>`

## Adding a New Stick Layout

1. Copy `sticks/default.toml` to `sticks/<myStick>.toml`
2. Adjust `x` / `y` values to match your cabinet
3. Set `stick = "myStick"` in `system.toml` or pass `--stick myStick` on the CLI

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| PyQt6 | ≥ 6.4 | Borderless window, QPainter rendering, file watcher |
| tomllib | built-in | TOML config parsing (Python 3.11+) |
| tomli | ≥ 2.0 | TOML parsing for Python < 3.11 |
| tomli-w | ≥ 1.0 | Clean config file writes from settings dialog (optional) |
| Pillow | ≥ 10.0 | Image loading (optional) |