"""
stickui.core.stick
~~~~~~~~~~~~~~~~~~
Loads a stick hardware layout config from sticks/<name>.toml
and resolves the final labels from system + game configs.

A StickLayout contains a flat list of InputSlot objects,
each with an absolute pixel position and a resolved label.
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
    id: str            # "up" / "down" / "left" / "right" / "b1" .. "b8"
    x: int
    y: int
    label: str         # resolved display label
    kind: str          # "direction" or "button"
    size: int = 0      # 0 = use global default from stick [display]


@dataclass
class StickLayout:
    name: str
    slots: list[InputSlot] = field(default_factory=list)
    arrow_size: int  = 36
    button_size: int = 52

    @property
    def directions(self) -> list[InputSlot]:
        return [s for s in self.slots if s.kind == "direction"]

    @property
    def buttons(self) -> list[InputSlot]:
        return [s for s in self.slots if s.kind == "button"]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        try:
            return tomllib.load(fh)
        except Exception:
            return {}


def load_stick_layout(
    stick_name: str,
    sticks_dir: Path,
    system_cfg: dict[str, Any],
    game_cfg:   dict[str, Any],
) -> StickLayout:
    """
    Load a stick .toml and resolve labels from system + game configs.

    Label priority (highest → lowest):
      game  [buttons] / [directions]
      system [buttons] / [directions]
      stick id as fallback
    """
    stick_path = sticks_dir / f"{stick_name}.toml"
    raw = _load_toml(stick_path)

    if not raw:
        # Return a minimal empty layout so the app doesn't crash
        return StickLayout(name=stick_name)

    display = raw.get("display", {})
    arrow_size  = int(display.get("arrow_size",  36))
    button_size = int(display.get("button_size", 52))

    # Resolved label maps (game wins over system)
    sys_dirs  = system_cfg.get("directions", {})
    sys_btns  = system_cfg.get("buttons",    {})
    game_dirs = game_cfg.get("directions",   {})
    game_btns = game_cfg.get("buttons",      {})

    def dir_label(slot_id: str) -> str:
        return game_dirs.get(slot_id) or sys_dirs.get(slot_id) or slot_id.capitalize()

    def btn_label(slot_id: str) -> str:
        return game_btns.get(slot_id) or sys_btns.get(slot_id) or slot_id.upper()

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
        slots.append(InputSlot(
            id    = sid,
            x     = int(entry.get("x", 0)),
            y     = int(entry.get("y", 0)),
            label = btn_label(sid),
            kind  = "button",
            size  = int(entry.get("size", 0)),
        ))

    return StickLayout(
        name        = raw.get("stick", {}).get("name", stick_name),
        slots       = slots,
        arrow_size  = arrow_size,
        button_size = button_size,
    )