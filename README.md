# StickUI

A borderless, always-on-top controller layout overlay for arcade sticks and emulators.
Displays a visual reference of button mappings for any system or game, positioned to match your physical cabinet layout.
**Auto-reloads when any config file is saved.**

```bash
python -m stickui --system mame --game ffight
python -m stickui --system snes --game "Super Mario World (Europe) (Rev 1)"
python -m stickui --system snes --stick myStick --width 700 --height 300
```

---

## Features

- **Borderless translucent overlay** — stays on top of your emulator
- **Auto-reload** — edit any config file and the UI updates instantly, no restart needed
- **Stick layout config** — define exact pixel positions for every button and direction arrow to match your physical cabinet
- **Three-tier label system** — stick defines positions, system defines default labels, game overrides specific labels
- **Edit mode** — click any button to edit its label, position, size, and colour live; save to `<game>.toml` with one click
- **Smart label fitting** — labels auto-size inside buttons; multi-word labels word-wrap to 2 lines; falls back to initials + external label only when necessary
- **Unused buttons** — set a label to `"Unused"` to render greyed out; `""` falls back to system default
- **Cardinal direction arrows** — ▲ ◀ ▼ ▶ with custom labels when a game remaps directions
- **Per-button colours** — each button can have its own colour (e.g. European SNES scheme)
- **Logo overlay** — floating PNG, does not affect button layout
- **Background image** — PNG or JPG, cover-scaled with configurable darkening overlay
- **LaunchBox integration** — auto-resolves game titles, logos and backgrounds from your LaunchBox library
- **MAME title lookup** — reads `mame.dat` for full arcade titles
- **command.dat integration** — auto-populates button labels from MAME's move list database
- **short_name** — use a short alias (e.g. `--system mame`) even when the system folder has a long name (e.g. `Arcade`)
- **Settings dialog** — corner button or right-click → Settings to adjust window size, position, opacity, auto-hide and background dim. Saves to the correct config file automatically
- **Draggable** — left-click drag to reposition
- **Right-click menu** — Settings, Edit Layout, Copy Position, Reload Now, Quit
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

Optional — cleaner config writes from the settings dialog and edit mode:

```bash
pip install tomli-w
```

---

## Running

```bash
# From the repo root:
python -m stickui --system mame --game ffight
python -m stickui --system snes --game "Super Mario World (Europe) (Rev 1)"
python -m stickui --system snes --stick myStick --xpos 50 --ypos 900 --width 620 --height 280
```

### CLI Flags

| Flag | Description |
|---|---|
| `--system` | System short name (e.g. `mame`, `snes`) — mapped via `short_name` in system.toml **(required)** |
| `--game` | ROM name without extension, or full filename stem for emulators like SNES |
| `--stick` | Stick config name in `sticks/` folder (default: from system.toml or `default`) |
| `--xpos` | Window X position (overrides config.toml) |
| `--ypos` | Window Y position (overrides config.toml) |
| `--width` | Window width in pixels |
| `--height` | Window height in pixels |

---

## Directory Structure

```
stickUI/                                        ← run from here
├── config.toml                                 ← global settings
├── sticks/
│   └── default.toml                            ← stick hardware layout
├── systems/
│   ├── Arcade/                                 ← folder name matches LaunchBox platform
│   │   ├── system.toml                         ← short_name = "mame"
│   │   ├── mame.png                            ← system logo fallback
│   │   ├── background.jpg
│   │   ├── ffight.png                          ← per-game logo override
│   │   └── sf2.toml                            ← per-game label overrides
│   ├── Super Nintendo Entertainment System/   ← matches LaunchBox platform name
│   │   ├── system.toml                         ← short_name = "snes"
│   │   ├── snes.png
│   │   └── background.jpg
│   ├── Sony Playstation/
│   │   └── system.toml                         ← short_name = "psx"
│   └── SNK Neo Geo AES/
│       └── system.toml                         ← short_name = "neogeo"
└── stickui/                                    ← Python package
    ├── __main__.py
    ├── core/
    │   ├── config.py
    │   ├── game_writer.py                      ← saves edited layouts to <game>.toml
    │   ├── layout.py
    │   ├── launchbox.py
    │   ├── mame_cfg.py
    │   ├── mame_dat.py
    │   ├── command_dat.py
    │   ├── stick.py
    │   └── watcher.py
    └── ui/
        ├── background.py
        ├── button_editor.py                    ← per-button edit dialog
        ├── panel.py
        ├── settings_dialog.py
        └── window.py
```

---

## Edit Mode

Edit mode lets you adjust every button's label, position, size, and colour directly in the overlay — no manual TOML editing required.

### Opening edit mode

- Click the **pencil button** (bottom-left corner of the overlay), or
- Right-click → **✏️ Edit Layout**

An edit bar appears at the top of the overlay:

```
✏  Edit Mode — click any button to edit    [💾 Save]  [↩ Revert]  [Done]
```

### Editing a button

Click any button or direction arrow to open the **Button Editor** dialog:

| Field | Description |
|---|---|
| **Label** | Text shown inside the button. Use `\n` to force a two-line split |
| **Symbol picker** | Quick-insert PS shapes (△□○✕), arrows (▲▼◀▶), and common symbols |
| **Mark as Unused** | Greys out the button immediately |
| **Size** | Button diameter in pixels. Steps by 2px |
| **X / Y** | Position relative to the top-left of the overlay window |
| **Colour / Border** | Fill and border colour (buttons only). Click to open colour picker |
| **Copy Style** | Copies the current size and colours to a clipboard |
| **Apply Style** | Pastes the copied size and colours onto this button |

- **Apply** — writes changes to the slot and repaints the overlay live; flashes green on success
- **Revert** — restores the button to its state when the dialog was opened
- **Close** — closes the dialog without saving to disk

### Saving and reverting

Changes accumulate in memory until you explicitly save or revert.

| Button | Action |
|---|---|
| **💾 Save** | Writes the current layout to `systems/<s>/<game>.toml`. Only values that differ from system defaults are written, keeping the file minimal. |
| **↩ Revert** | Discards all unsaved edits and reloads from disk |
| **Done** | Exits edit mode without saving |

> **Note:** Save creates or replaces `[buttons]`, `[directions]`, and `[button_colors]` sections while preserving any existing `[game]` and `[display]` sections.

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
auto_hide_seconds = 0

# Background image darkening (0.0 = original, 1.0 = black, default 0.55)
background_dim = 0.55

[paths]
systems_dir  = './systems'
mame_cfg_dir = 'd:/mame/cfg'

# Path to MAME's XML data file (mame.dat or mame.xml)
mame_dat = 'd:/mame/mame.dat'

# Path to command.dat (MAME move list / button name database)
command_dat = 'd:/mame/dats/command.dat'

# LaunchBox root folder (must contain LaunchBox.exe) — used by all systems
launchbox_dir = 'D:/LaunchBox'
```

> **Windows paths:** always use forward slashes or single-quoted strings.

---

### `sticks/<n>.toml` — Hardware layout

```toml
[stick]
name        = "Default 4+8 Arcade Stick"
description = "Select+Start at top, 4-way stick, 2 rows of 4 buttons"

[[buttons]]
id   = "select"
x    = 80
y    = 40
size = 34

[[buttons]]
id   = "start"
x    = 140
y    = 40
size = 34

[[directions]]
id = "up"
x  = 100
y  = 130

# ... left / right / down ...

[[buttons]]
id = "b1"
x  = 300
y  = 140

# ... b2 through b8 ...

[display]
arrow_size   = 39
button_size  = 60
```

**Direction ids:** `up`, `down`, `left`, `right`
**Button ids:** `select`, `start`, `b1`–`b8`

Drag the window into position, right-click → **Copy Position** to get coordinates,
then measure button offsets from the window's top-left corner.

---

### `systems/<s>/system.toml` — System defaults

```toml
[system]
name               = "MAME"
short_name         = "mame"        # --system flag value
description        = "Multiple Arcade Machine Emulator"
logo               = "logo.png"    # fallback system logo
background         = "background.jpg"
stick              = "default"
launchbox_platform = 'Arcade'      # matches Data/Platforms/<n>.xml

[display]
button_color        = "#e63946"
button_label_color  = "#ffffff"
button_border_color = "#ff6b6b"
stick_color         = "#2b2d42"
panel_color         = "#0d0d0d"
background_dim      = 0.6          # override global dim for this system
logo_height         = 128
logo_x              = -1           # -1 = auto right-align
logo_y              = 8
logo_margin         = 12
logo_opacity        = 0.9
show_system_name    = true
title_font_size     = 14
subtitle_font_size  = 9

[directions]
up    = "Up"
down  = "Down"
left  = "Left"
right = "Right"

[buttons]
b1     = "A"
b2     = "B"
b3     = "C"
b4     = "X"
b5     = "Y"
b6     = "Z"
b7     = "D"
b8     = "E"
select = "Insert Coin"
start  = "1P Start"

# Maps command.dat button abbreviations to stick slots (MAME only)
[command_dat_map]
LP = "b1"
MP = "b2"
HP = "b3"
LK = "b5"
MK = "b6"
HK = "b7"
```

#### European SNES colour scheme example

```toml
[button_colors]
b1 = { color = "#d4a017", border = "#f0c040" }   # Y — Yellow
b2 = { color = "#5ba4cf", border = "#89c4e8" }   # X — Light Blue
b3 = { color = "#555555", border = "#888888" }   # L — Grey
b4 = { color = "#555555", border = "#888888" }   # R — Grey
b5 = { color = "#2e8b3e", border = "#4ab85e" }   # B — Green
b6 = { color = "#c0392b", border = "#e05040" }   # A — Red
```

---

### `systems/<s>/<game>.toml` — Per-game overrides

```toml
[game]
name = "Street Fighter II"   # omit to use LaunchBox/mame.dat title
logo = "sf2.png"             # omit to use LaunchBox Clear Logo

[display]
button_color   = "#dc2626"
background_dim = 0.75        # darker for this specific game

[buttons]
b1 = "Light\nPunch"   # \n splits onto two lines inside the button
b2 = "Med\nPunch"
b3 = "Heavy\nPunch"
b4 = "Unused"         # greyed out — no function in this game
b5 = "Light\nKick"
b6 = "Med\nKick"
b7 = "Heavy\nKick"
b8 = "Unused"
select = ""           # empty = fall back to system default
start  = ""

[directions]
up   = "Jump"
down = "Crouch"
```

---

## Button Labels

| Value | Behaviour |
|---|---|
| `"Light Punch"` | Displayed as-is, auto-sized to fit |
| `"Light\nPunch"` | Forced two-line split |
| `""` (empty) | Falls back to system default, then stick id |
| `"Unused"` | Greyed-out button |

**Fitting order:** single line → two-line word wrap → initials inside + full label below.

**Label priority (highest → lowest):**

| Source | Example |
|---|---|
| `<game>.toml [buttons]` | `b1 = "Light\nPunch"` |
| command.dat CONTROLS section | `_A : Attack` → b1 |
| `system.toml [buttons]` | `b1 = "A"` |
| Stick slot id | `"b1"` |

If the ROM is found in command.dat, any button not defined there is automatically set to `"Unused"`. This does not affect `select`, `start` or directions.

---

## LaunchBox Integration

Set `launchbox_dir` once in `config.toml` and `launchbox_platform` in each `system.toml`.

```toml
# config.toml
launchbox_dir = 'D:/LaunchBox'

# systems/Arcade/system.toml
launchbox_platform = 'Arcade'

# systems/Super Nintendo Entertainment System/system.toml
launchbox_platform = 'Super Nintendo Entertainment System'
```

StickUI reads `Data/Platforms/<platform>.xml` to map ROM filenames to:
- **Game title** — from `<Title>` tag
- **Region** — from `<Region>` tag (used to guide image search)

### Image search order

For both logos and backgrounds, images are searched in this folder order inside the category directory (`Clear Logo/` or `Fanart - Background/`):

| Priority | Folder |
|---|---|
| 1 | Root of category (no subfolder) |
| 2 | `World/` |
| 3 | Region from XML (e.g. `Europe/`) |
| 4 | `North America/` |
| 5 | Any other subfolder (alphabetical) |

Filenames matched (case-insensitive): `<Title>-01.png`, `<Title>-02.png`, `<Title>.png`.
LaunchBox replaces `:` and other illegal filename characters with `_`, e.g.:
`Street Fighter II: The World Warrior` → `Street Fighter II_ The World Warrior-01.png`

### Asset priority (logos)

| Priority | Source |
|---|---|
| 1 | `systems/<s>/<game>.png` — local override |
| 2 | LaunchBox Clear Logo |
| 3 | `systems/<s>/logo.png` or `<s>.png` — system fallback |

### Asset priority (backgrounds)

| Priority | Source |
|---|---|
| 1 | `[game] background` in `<game>.toml` |
| 2 | `<game>_bg.png/jpg` in system folder |
| 3 | LaunchBox Fanart - Background |
| 4 | `system.toml [system] background` / `background.jpg` |
| 5 | Gradient from `panel_color` |

---

## MAME Title Lookup

When `mame_dat` is configured, the full arcade title is resolved from the dat file:

```
--game ffight  →  "Final Fight (World, set 1)"
--game sf2     →  "Street Fighter II: The World Warrior (World 910522)"
```

Title priority: `[game] name` → LaunchBox XML → mame.dat → ROM filename.

---

## command.dat Integration (MAME only)

When `command_dat` is configured and `--system mame` is used, button labels are
auto-populated from the CONTROLS section of command.dat.

Supported formats: `_A : Label`, `^E : Label`, `@F-button : Label`, `_B(LP)`.

If the ROM is in command.dat, buttons not defined there are automatically greyed out as `Unused`. Per-game `.toml` overrides always take priority over command.dat.

---

## short_name — System Folder Aliases

System folders can be named to match LaunchBox platform names exactly, while still
being invoked with a short `--system` flag:

```toml
# systems/Arcade/system.toml
[system]
short_name = "mame"

# systems/Super Nintendo Entertainment System/system.toml
[system]
short_name = "snes"
```

```bash
python -m stickui --system mame   # loads systems/Arcade/
python -m stickui --system snes   # loads systems/Super Nintendo Entertainment System/
```

---

## Background Darkening

Background images from LaunchBox fanart are often very bright. Control the darkening
overlay with `background_dim` (0.0 = original, 1.0 = black):

```toml
# config.toml — global default
background_dim = 0.55

# system.toml [display] — per system
background_dim = 0.6

# game.toml [display] — per game
background_dim = 0.75
```

Also adjustable live in the Settings dialog (corner button or right-click → Settings).
The dialog shows which file will be written to.

---

## Settings Dialog

Open via the **invisible button in the bottom-right corner**, or right-click → **⚙️ Settings**.

| Control | Description |
|---|---|
| X / Y | Window position. `[−]` / `[+]` step by 10px |
| Width / Height | Window size. Steps by 10px |
| Capture button | Snaps fields to the current live position and size |
| Opacity slider | 5%–100% |
| Dim slider | Background darkening 0%–100%. Label shows which file will be saved |
| Auto-hide | Enable and set delay (1–120s) |
| Apply && Save | Writes changes and applies immediately |

---

## Auto-Reload

Watches all active config files. Save any of them and the UI refreshes within 300ms.

- `config.toml`
- `systems/<s>/system.toml`
- `systems/<s>/<game>.toml`
- `sticks/<n>.toml`

Force a reload via right-click → **🔄 Reload Now**.

---

## Controls

| Action | How |
|---|---|
| Move window | Left-click drag |
| Close | ESC |
| Open settings | Click bottom-right corner, or right-click → Settings |
| Toggle edit mode | Click bottom-left corner (pencil), or right-click → Edit Layout |
| Edit a button | Enter edit mode, then click the button |
| Copy window position | Right-click → Copy Position |
| Force reload | Right-click → Reload Now |
| Quit | Right-click → Quit |

---

## Adding a New System

1. Create `systems/<LaunchBox platform name>/`
2. Add `system.toml` with `short_name`, `launchbox_platform`, buttons and colours
3. Optionally add `<short_name>.png` and `background.jpg`
4. Run: `python -m stickui --system <short_name>`

## Adding a New Stick Layout

1. Copy `sticks/default.toml` to `sticks/<myStick>.toml`
2. Adjust `x` / `y` values to match your cabinet
3. Set `stick = "myStick"` in `system.toml` or pass `--stick myStick`

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| PyQt6 | ≥ 6.4 | Borderless window, QPainter, file watcher |
| tomllib | built-in | TOML parsing (Python 3.11+) |
| tomli | ≥ 2.0 | TOML parsing for Python < 3.11 |
| tomli-w | ≥ 1.0 | Clean config writes from settings dialog and edit mode (optional) |
| Pillow | ≥ 10.0 | Image loading (optional) |
