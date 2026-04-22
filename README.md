# StickUI

A borderless, always-on-top controller layout overlay for arcade sticks and emulators.
Displays a visual reference of button mappings for any system or game, positioned to match your physical cabinet layout.

```bash
python -m stickui --system snes
python -m stickui --system mame --game sf2
python -m stickui --system snes --stick myStick --width 700 --height 300
```

---

## Features

- **Borderless translucent overlay** — stays on top of your emulator
- **Stick layout config** — define exact pixel positions for every button and direction arrow to match your physical cabinet
- **Three-tier label system** — stick defines positions, system defines default labels, game overrides specific labels
- **Cardinal direction arrows** — ▲ ◀ ▼ ▶ with custom labels when a game remaps directions
- **Logo support** — game or system PNG shown in the header
- **Background image** — per-system or per-game
- **Draggable** — left-click drag to reposition
- **Right-click menu** — Copy Position (outputs ready-to-use CLI flags), Quit
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
│   │   ├── logo.png              ← system logo (optional)
│   │   ├── background.png        ← system background (optional)
│   │   └── sf2.toml              ← per-game label overrides
│   └── snes/
│       ├── system.toml
│       ├── logo.png
│       └── background.png
└── stickui/                      ← Python package (don't edit unless developing)
    ├── __main__.py
    ├── core/
    │   ├── config.py
    │   ├── layout.py
    │   ├── mame_parser.py
    │   └── stick.py
    └── ui/
        ├── window.py
        └── panel.py
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

---

### `sticks/<name>.toml` — Hardware layout

Defines where every input appears on screen in pixels, relative to the top-left of the window. Tune these to match your physical cabinet.

```toml
[stick]
name        = "Default 4+8 Arcade Stick"
description = "Select+Start at top, 4-way stick, 2 rows of 4 buttons"

# Small meta buttons at the top
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

# ... left / down / right ...

# Main action buttons
[[buttons]]
id = "b1"
x  = 300
y  = 140

# ... b2 through b8 ...

[display]
arrow_size   = 34   # default arrow button size
button_size  = 52   # default action button diameter
```

**Button ids:** `select`, `start`, `b1` – `b8`  
**Direction ids:** `up`, `down`, `left`, `right`

To find the right positions: run the app, drag the window where you want it, right-click → **Copy Position** to get the window coordinates, then measure button offsets relative to the window's top-left corner.

---

### `systems/<system>/system.toml` — System defaults

```toml
[system]
name   = "Super Nintendo"
stick  = "default"        # which stick layout to use
logo   = "logo.png"
background = "background.png"

[display]
button_color        = "#8b5cf6"
button_label_color  = "#ffffff"
button_border_color = "#a78bfa"
stick_color         = "#1e1b4b"
panel_color         = "#111827"

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

### `systems/<system>/<game>.toml` — Per-game overrides

Only include what differs from the system defaults.

```toml
[game]
name = "Street Fighter II"
logo = "sf2.png"

[buttons]
b1 = "Light Punch"
b2 = "Medium Punch"
b3 = "Heavy Punch"
b4 = "Light Kick"
b5 = "Medium Kick"
b6 = "Heavy Kick"
```

---

## Label Priority (highest → lowest)

| Source | Applies to |
|---|---|
| CLI flags | Window position/size |
| `<game>.toml` `[buttons]` / `[directions]` | Labels |
| MAME `.cfg` XML | Labels (MAME only, when no game override) |
| `system.toml` `[buttons]` / `[directions]` | Labels |
| `sticks/<n>.toml` | Button positions and sizes |
| `config.toml` | Window defaults, paths |

---

## Controls

| Action | How |
|---|---|
| Move window | Left-click drag |
| Close | ESC |
| Context menu | Right-click |
| Copy window position | Right-click → Copy Position |

---

## Adding a New System

1. Create `systems/<system_id>/`
2. Add `system.toml` (copy from `snes/` and adapt labels)
3. Optionally add `logo.png` and `background.png`
4. Run: `python -m stickui --system <system_id>`

## Adding a New Stick Layout

1. Copy `sticks/default.toml` to `sticks/<myStick>.toml`
2. Adjust `x` / `y` positions to match your cabinet
3. Reference it in `system.toml` with `stick = "myStick"` or pass `--stick myStick` on the CLI

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| PyQt6 | ≥ 6.4 | Borderless window + QPainter rendering |
| tomllib | built-in | TOML config parsing (Python 3.11+) |
| tomli | ≥ 2.0 | TOML parsing for Python < 3.11 |
| Pillow | ≥ 10.0 | Image loading (optional) |