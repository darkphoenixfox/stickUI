# ControlPad

A borderless, always-on-top controller layout overlay for MAME and other emulators.

```
python -m controlpad --system mame --game sf2
python -m controlpad --system snes --game smw --width 900 --height 500
```

---

## Features

- **Borderless translucent overlay** – stays on top of your game / emulator window
- **Three layout modes**: `arcade` (joystick + button grid), `gamepad` (SNES-style), `grid`
- **Three-tier config hierarchy**: global → system → per-game (each level overrides the previous)
- **MAME .cfg parser** – auto-reads button assignments from MAME's own config files as a fallback
- **Logo support** – displays a game or system logo PNG in the header
- **Background image support** – per-system or per-game background
- **Draggable** – left-click drag to reposition; right-click → "Copy Position" to save coordinates
- **ESC** to close

---

## Installation

```bash
pip install -r requirements.txt
```

Python 3.11+ is recommended (ships with `tomllib`). For Python 3.9/3.10, also run:

```bash
pip install tomli
```

---

## Running

```bash
# From the project root:
python -m controlpad --system mame --game sf2

# With explicit position / size:
python -m controlpad --system snes --game smw --xpos 50 --ypos 900 --width 760 --height 420

# Using a custom global config:
python -m controlpad --system mame --game sf2 --config /path/to/config.toml
```

---

## Directory Structure

```
~/.config/controlpad/
├── config.toml                  ← global settings (paths, default window size)
└── systems/
    ├── mame/
    │   ├── system.toml          ← MAME-wide defaults, colours, layout style
    │   ├── logo.png             ← system logo (shown when no game logo)
    │   ├── background.png       ← system background
    │   ├── sf2.toml             ← per-game overrides for Street Fighter II
    │   ├── sf2.png              ← game logo
    │   └── mk.toml              ← per-game overrides for Mortal Kombat
    └── snes/
        ├── system.toml
        ├── logo.png
        ├── background.png
        └── smw.toml             ← per-game overrides for Super Mario World
```

---

## Config Reference

### `config.toml` (global)

```toml
[general]
xpos   = 100
ypos   = 100
width  = 800
height = 480
opacity = 0.92
auto_hide_seconds = 0   # 0 = never hide

[paths]
systems_dir    = "~/.config/controlpad/systems"
mame_cfg_dir   = "~/.mame/cfg"
mame_ctrlr_dir = "~/.mame/ctrlr"
```

### `system.toml`

```toml
[system]
name       = "MAME"
logo       = "logo.png"
background = "background.png"

[display]
layout_style        = "arcade"    # arcade | gamepad | grid
button_shape        = "circle"
button_color        = "#e63946"
button_label_color  = "#ffffff"
button_border_color = "#ff6b6b"
stick_color         = "#2b2d42"
panel_color         = "#0d0d0d"

[defaults.buttons]
"BUTTON1" = "A"
"BUTTON2" = "B"
# … etc.
```

### `<game>.toml` (per-game override)

```toml
[game]
name = "Street Fighter II"
logo = "sf2.png"

[display]
button_color = "#dc2626"   # override just the button colour for this game

[buttons]
"BUTTON1" = "Light\nPunch"
"BUTTON2" = "Medium\nPunch"
"BUTTON3" = "Heavy\nPunch"
"BUTTON4" = "Light\nKick"
"BUTTON5" = "Medium\nKick"
"BUTTON6" = "Heavy\nKick"

[layout]
# [col, row] positions in the button grid (optional)
"BUTTON1" = [0, 1]
"BUTTON2" = [1, 1]
"BUTTON3" = [2, 1]
"BUTTON4" = [0, 0]
"BUTTON5" = [1, 0]
"BUTTON6" = [2, 0]
```

---

## Config Priority (highest → lowest)

| Source              | Notes                                              |
|---------------------|----------------------------------------------------|
| CLI flags           | `--xpos`, `--ypos`, `--width`, `--height`         |
| `<game>.toml`       | Per-game labels, layout positions, display tweaks  |
| MAME `.cfg` file    | Auto-parsed if system=mame and no game override    |
| `system.toml`       | System-wide defaults and display settings          |
| `config.toml`       | Global paths and window defaults                   |
| Built-in defaults   | Hard-coded fallback values in the Python code      |

---

## Keyboard & Mouse Controls

| Action              | How                                      |
|---------------------|------------------------------------------|
| Move window         | Left-click drag                          |
| Close               | ESC key                                  |
| Context menu        | Right-click                              |
| Copy position       | Right-click → "Copy Position"            |

---

## Adding a New System

1. Create `~/.config/controlpad/systems/<system_id>/`
2. Add `system.toml` (copy from an existing system and adapt)
3. Optionally add `logo.png` and `background.png`
4. Run: `python -m controlpad --system <system_id>`

---

## Dependencies

| Package    | Version  | Purpose                        |
|------------|----------|--------------------------------|
| PyQt6      | ≥ 6.4    | Borderless window + QPainter   |
| tomllib    | built-in | TOML config parsing (Py 3.11+) |
| tomli      | ≥ 2.0    | TOML parsing for Py < 3.11     |
| Pillow     | ≥ 10.0   | Image loading (optional)       |