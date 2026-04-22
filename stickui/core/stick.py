"""
stickui.core.stick
~~~~~~~~~~~~~~~~~~
Loads a stick hardware layout config and resolves labels from:
  1. game.toml   [buttons] / [directions]
  2. system.toml [buttons] / [directions]
  3. command.dat (MAME only — button names from move list database)
  4. Stick slot id as last resort

Empty string in game.toml falls through to the next level.
"Unused" renders the button greyed out.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class InputSlot:
    id: str
    x: int
    y: int
    label: str
    kind: str          # "direction" or "button"
    size: int = 0
    color: str = ""    # per-button override, empty = use system default
    border: str = ""   # per-button border override


@dataclass
class StickLayout:
    name: str
    slots: list[InputSlot] = field(default_factory=list)
    arrow_size: int  = 39
    button_size: int = 60

    @property
    def directions(self) -> list[InputSlot]:
        return [s for s in self.slots if s.kind == "direction"]

    @property
    def buttons(self) -> list[InputSlot]:
        return [s for s in self.slots if s.kind == "button"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        try:
            return tomllib.load(fh)
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_stick_layout(
    stick_name:  str,
    sticks_dir:  Path,
    system_cfg:  dict[str, Any],
    game_cfg:    dict[str, Any],
    rom_name:    str | None = None,
    command_dat: Path | None = None,
) -> StickLayout:
    """
    Load stick .toml and resolve labels.

    Label priority (highest → lowest):
      1. game.toml   [buttons] / [directions]   — empty string falls through
      2. system.toml [buttons] / [directions]
      3. command.dat button names               (MAME only, when provided)
      4. Stick slot id
    """
    stick_path = sticks_dir / f"{stick_name}.toml"
    raw = _load_toml(stick_path)

    if not raw:
        return StickLayout(name=stick_name)

    display     = raw.get("display", {})
    arrow_size  = int(display.get("arrow_size",  39))
    button_size = int(display.get("button_size", 60))

    # System labels — support both [buttons] and legacy [defaults.buttons]
    sys_btns = (system_cfg.get("buttons")
                or system_cfg.get("defaults", {}).get("buttons", {}))
    sys_dirs = (system_cfg.get("directions")
                or system_cfg.get("defaults", {}).get("axes", {}))

    game_btns = game_cfg.get("buttons",    {})
    game_dirs = game_cfg.get("directions", {})

    # command.dat labels (MAME only, fallback before slot id)
    cmd_labels: dict[str, str] = {}
    cmd_found = False   # True if the ROM exists in command.dat at all
    if rom_name and command_dat and command_dat.is_file():
        try:
            from .command_dat import resolve_button_labels, lookup as cmd_lookup, FIGHTER_6BTN_MAP
            sys_map = system_cfg.get("command_dat_map") or FIGHTER_6BTN_MAP
            cmd_labels = resolve_button_labels(rom_name, command_dat, btn_map=sys_map)
            cmd_found  = cmd_lookup(rom_name, command_dat) is not None
        except Exception as e:
            print(f"[stickui] command.dat lookup error: {e}")

    # All action button slot ids on this stick
    _ACTION_SLOTS = {"b1","b2","b3","b4","b5","b6","b7","b8"}

    def dir_label(slot_id: str) -> str:
        return (game_dirs.get(slot_id)
                or sys_dirs.get(slot_id)
                or slot_id.capitalize())

    def btn_label(slot_id: str) -> str:
        # Priority: game toml > command.dat > system.toml > slot id
        # If the ROM is in command.dat but this button is not defined there,
        # mark it as Unused (only for action buttons b1–b8, not select/start)
        game_val = game_btns.get(slot_id)
        if game_val:
            return game_val

        if cmd_found and slot_id in _ACTION_SLOTS:
            # ROM is in command.dat — only show buttons defined there
            cmd_val = cmd_labels.get(slot_id)
            return cmd_val if cmd_val else "Unused"

        return (sys_btns.get(slot_id)
                or slot_id.upper())

    slots: list[InputSlot] = []

    for entry in raw.get("directions", []):
        sid = entry.get("id", "")
        slots.append(InputSlot(
            id    = sid,
            x     = int(entry.get("x", 0)),
            y     = int(entry.get("y", 0)),
            label = dir_label(sid),
            kind  = "direction",
            size  = int(entry.get("size", 0)),
        ))

    for entry in raw.get("buttons", []):
        sid = entry.get("id", "")
        btn_color_cfg = system_cfg.get("button_colors", {}).get(sid, {})
        # game.toml can also override colors
        game_color_cfg = game_cfg.get("button_colors", {}).get(sid, {})
        merged_color = {**btn_color_cfg, **game_color_cfg}

        slots.append(InputSlot(
            id     = sid,
            x      = int(entry.get("x", 0)),
            y      = int(entry.get("y", 0)),
            label  = btn_label(sid),
            kind   = "button",
            size   = int(entry.get("size", 0)),
            color  = merged_color.get("color", ""),
            border = merged_color.get("border", ""),
        ))

    return StickLayout(
        name        = raw.get("stick", {}).get("name", stick_name),
        slots       = slots,
        arrow_size  = arrow_size,
        button_size = button_size,
    )