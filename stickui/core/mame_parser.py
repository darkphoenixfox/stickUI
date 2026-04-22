"""
controlpad.core.mame_parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Parses MAME's per-game .cfg XML files to extract button port assignments.

MAME cfg files look like:

  <mameconfig version="10">
    <system name="sf2">
      <input>
        <port tag=":IN0" type="P1_BUTTON1" mask="16" defvalue="16">
          <newseq type="standard">KEYCODE_Z</newseq>
        </port>
        ...
      </input>
    </system>
  </mameconfig>
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional


# Maps MAME port type → human-friendly default label
_DEFAULT_LABELS: Dict[str, str] = {
    "P1_BUTTON1": "Button 1",
    "P1_BUTTON2": "Button 2",
    "P1_BUTTON3": "Button 3",
    "P1_BUTTON4": "Button 4",
    "P1_BUTTON5": "Button 5",
    "P1_BUTTON6": "Button 6",
    "P1_JOYSTICK_UP":    "Up",
    "P1_JOYSTICK_DOWN":  "Down",
    "P1_JOYSTICK_LEFT":  "Left",
    "P1_JOYSTICK_RIGHT": "Right",
    "P1_START":  "1P Start",
    "COIN1":     "Insert Coin",
    "P2_BUTTON1": "2P Button 1",
    "P2_BUTTON2": "2P Button 2",
    "P2_BUTTON3": "2P Button 3",
    "P2_BUTTON4": "2P Button 4",
    "P2_BUTTON5": "2P Button 5",
    "P2_BUTTON6": "2P Button 6",
    "P2_START":  "2P Start",
}

# Map MAME P1_BUTTONx → simple BUTTON key used in system.toml defaults
_MAME_TO_GENERIC: Dict[str, str] = {
    "P1_BUTTON1": "BUTTON1",
    "P1_BUTTON2": "BUTTON2",
    "P1_BUTTON3": "BUTTON3",
    "P1_BUTTON4": "BUTTON4",
    "P1_BUTTON5": "BUTTON5",
    "P1_BUTTON6": "BUTTON6",
    "P1_JOYSTICK_UP":    "JOYSTICK_LEFT_UP",
    "P1_JOYSTICK_DOWN":  "JOYSTICK_LEFT_DOWN",
    "P1_JOYSTICK_LEFT":  "JOYSTICK_LEFT_LEFT",
    "P1_JOYSTICK_RIGHT": "JOYSTICK_LEFT_RIGHT",
    "P1_START": "START1",
    "COIN1":    "COIN1",
}


def parse_mame_cfg(cfg_path: Path) -> Dict[str, str]:
    """
    Parse a MAME .cfg file and return a {generic_button_id: label} dict.

    Only P1 inputs are returned.  The labels are human-readable defaults
    extracted from the port type name; MAME cfg files do not store display
    labels, so callers should layer their own labels on top.
    """
    if not cfg_path.is_file():
        return {}

    try:
        tree = ET.parse(cfg_path)
    except ET.ParseError:
        return {}

    root = tree.getroot()
    result: Dict[str, str] = {}

    for port in root.iter("port"):
        port_type: Optional[str] = port.get("type")
        if not port_type:
            continue

        generic_key = _MAME_TO_GENERIC.get(port_type)
        if generic_key:
            label = _DEFAULT_LABELS.get(port_type, port_type)
            result[generic_key] = label

    return result


def find_mame_cfg(cfg_dir: Path, game: str) -> Optional[Path]:
    """
    Locate the MAME cfg file for *game* inside *cfg_dir*.
    Returns the Path if found, else None.
    """
    candidates = [
        cfg_dir / f"{game}.cfg",
        cfg_dir / game / f"{game}.cfg",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None