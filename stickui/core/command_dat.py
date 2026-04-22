"""
stickui.core.command_dat
~~~~~~~~~~~~~~~~~~~~~~~~
Parses command.dat (MAME move list database) to extract button name
mappings for a given game.

Button code conventions in command.dat
---------------------------------------
Controls section uses these prefixes in "- CONTROLS -" sections only:

  _A : Label   — button slot A (b1)
  _B : Label   — button slot B (b2)
  _C : Label   — button slot C (b3)
  _D : Label   — button slot D (b4)
  _E : Label   — button slot E (b5)  (some games)
  _F : Label   — button slot F (b6)  (some games)

  ^E : Label   — button 1 (6-button fighter layout, starts at E)
  ^F : Label   — button 2
  ^G : Label   — button 3
  ^H : Label   — button 4
  ^I : Label   — button 5
  ^J : Label   — button 6

  ^s : Label   — special/extra button (lower-case s = extra button)
  ^S : Label   — select button (skip)
  _S : Label   — start button (skip)

  @F-button : Label   — named button F (fire)
  @J-button : Label   — named button J (jump)
  @E-button : Label   — named button E
  @L-button : Label   — named button L (light punch in some games)
  @X-button : Label   — named button X
  @R-button : Label   — named button R
  @O-button : Label   — named button O
  @M-button : Label   — named button M
  @W-button : Label   — named button W
  @Y-button : Label   — named button Y

We only parse lines inside "- CONTROLS -" sections to get clean
button definitions, ignoring move list lines which use the same codes
in combo notation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


_cache: dict[str, dict[str, "GameCommands"]] = {}


@dataclass
class GameCommands:
    rom_name:     str
    button_names: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Button code → stick slot mappings
# ---------------------------------------------------------------------------

# Underscore letter codes: _A=b1, _B=b2 ... _H=b8
_UNDERSCORE_MAP = {
    "_A": "b1", "_B": "b2", "_C": "b3", "_D": "b4",
    "_E": "b5", "_F": "b6", "_G": "b7", "_H": "b8",
}

# Caret letter codes: ^E=b1, ^F=b2, ^G=b3, ^H=b4, ^I=b5, ^J=b6
# (6-button fighter layout, starts from E)
# Also ^s = extra/special button → b7 or b8 area
_CARET_MAP = {
    "^E": "b1", "^F": "b2", "^G": "b3",
    "^H": "b4", "^I": "b5", "^J": "b6",
    "^s": "b7",
}

# @X-button codes → common single-button games
# These vary by game so we map them sequentially as encountered
_AT_MAP = {
    "@F-button": "b1",
    "@J-button": "b2",
    "@E-button": "b1",
    "@L-button": "b1",
    "@X-button": "b2",
    "@R-button": "b3",
    "@O-button": "b4",
    "@M-button": "b5",
    "@W-button": "b6",
    "@Y-button": "b7",
}

# Codes to skip entirely
_SKIP_CODES = {"_S", "^S", "_s"}


def _slot_for_code(code: str) -> Optional[str]:
    """Return the stick slot id for a button code, or None to skip."""
    if code in _SKIP_CODES:
        return None
    return (_UNDERSCORE_MAP.get(code)
            or _CARET_MAP.get(code)
            or _AT_MAP.get(code))


def _clean_label(label: str) -> str:
    """Strip trailing notes like (_P) (_K) (^s) from labels."""
    label = re.sub(r"\s*\([^)]*\)\s*$", "", label).strip()
    return label


def _parse_file(dat_path: Path) -> dict[str, GameCommands]:
    key = str(dat_path)
    if key in _cache:
        return _cache[key]

    result: dict[str, GameCommands] = {}

    try:
        text = dat_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"[stickui] command.dat read error: {e}")
        _cache[key] = result
        return result

    # Split on $info= markers
    blocks = re.split(r"(?m)^\$info=", text)

    for block in blocks[1:]:
        lines = block.splitlines()
        if not lines:
            continue

        rom_names = [r.strip() for r in lines[0].split(",") if r.strip()]

        in_cmd        = False
        in_controls   = False
        btn_names: dict[str, str] = {}

        for line in lines[1:]:
            stripped = line.strip()

            if stripped.startswith("$cmd"):
                in_cmd = True
                continue
            if stripped.startswith("$end"):
                break
            if not in_cmd:
                continue

            # Track whether we're inside the CONTROLS section
            if "- CONTROLS -" in stripped or "- CONTROLES -" in stripped:
                in_controls = True
                continue

            # Any new section heading ends the controls block
            if re.match(r"^-\s+.+\s+-\s*$", stripped) and in_controls:
                in_controls = False
                continue

            # Only parse button definitions inside CONTROLS section
            if not in_controls:
                continue

            if not stripped or stripped.startswith(";"):
                continue

            # Match:  CODE : Label
            # CODE can be: _A  ^E  @F-button  etc.
            m = re.match(
                r"^(@\w[\w-]*|[_^][A-Za-z0-9])\s*:\s*(.+)$",
                stripped
            )
            if not m:
                continue

            code  = m.group(1)
            label = _clean_label(m.group(2).strip())

            if not label:
                continue

            slot = _slot_for_code(code)
            if slot and slot not in btn_names:
                btn_names[slot] = label

        for rom in rom_names:
            result[rom] = GameCommands(
                rom_name     = rom,
                button_names = dict(btn_names),
            )

    _cache[key] = result
    return result


def lookup(rom_name: str, dat_path: Path) -> Optional[GameCommands]:
    if not dat_path or not dat_path.is_file():
        return None
    db = _parse_file(dat_path)
    return db.get(rom_name)


def resolve_button_labels(
    rom_name: str,
    dat_path: Path,
    btn_map: dict | None = None,
) -> dict[str, str]:
    """Return {slot_id: label} for rom_name. btn_map is unused (kept for compat)."""
    cmds = lookup(rom_name, dat_path)
    if not cmds:
        return {}
    return dict(cmds.button_names)


FIGHTER_6BTN_MAP: dict[str, str] = {
    "LP": "b1", "MP": "b2", "HP": "b3",
    "LK": "b5", "MK": "b6", "HK": "b7",
}