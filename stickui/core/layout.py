"""
controlpad.core.layout
~~~~~~~~~~~~~~~~~~~~~~
Resolves the final set of buttons to render and their positions.

Priority for button labels:
  game .toml  >  mame .cfg  >  system defaults

Priority for positions:
  game .toml [layout]  >  system.toml [layout]  >  built-in style templates
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import ConfigLoader
from .mame_parser import find_mame_cfg, parse_mame_cfg
from .mame_dat import lookup as mame_dat_lookup


@dataclass
class ButtonInfo:
    id: str
    label: str
    col: int = 0
    row: int = 0
    color: Optional[str] = None
    is_axis: bool = False


@dataclass
class LayoutResult:
    system_name: str
    game_name: str
    style: str
    buttons: List[ButtonInfo] = field(default_factory=list)
    logo_path: Optional[Path] = None
    background_path: Optional[Path] = None
    panel_color: str = "#0d0d0d"
    button_color: str = "#e63946"
    button_label_color: str = "#ffffff"
    button_border_color: str = "#ff6b6b"
    stick_color: str = "#2b2d42"


_ARCADE_6_POSITIONS: Dict[str, Tuple[int, int]] = {
    "BUTTON4": (0, 0), "BUTTON5": (1, 0), "BUTTON6": (2, 0),
    "BUTTON1": (0, 1), "BUTTON2": (1, 1), "BUTTON3": (2, 1),
}

_GAMEPAD_POSITIONS: Dict[str, Tuple[int, int]] = {
    "B": (1, 2), "A": (2, 1),
    "Y": (0, 1), "X": (1, 0),
    "L": (0, 0), "R": (2, 0),
    "SELECT": (0, 3), "START": (1, 3),
}

_STYLE_TEMPLATES: Dict[str, Dict[str, Tuple[int, int]]] = {
    "arcade":  _ARCADE_6_POSITIONS,
    "gamepad": _GAMEPAD_POSITIONS,
}


class LayoutResolver:
    def __init__(self, cfg: ConfigLoader) -> None:
        self.cfg = cfg

    def resolve(self) -> LayoutResult:
        cfg = self.cfg

        labels: Dict[str, str] = {}
        labels.update(cfg.buttons)
        labels.update(cfg.axes)

        if cfg.system == "mame" and cfg.game:
            game_buttons_overridden = bool(cfg._game_cfg.get("buttons"))
            if not game_buttons_overridden:
                mame_cfg_path = find_mame_cfg(cfg.mame_cfg_dir, cfg.game)
                if mame_cfg_path:
                    mame_labels = parse_mame_cfg(mame_cfg_path)
                    labels.update(mame_labels)

        # Priority: game [layout] > system [layout] > built-in template
        system_layout = cfg._system_cfg.get("layout", {})
        game_layout = cfg.layout_positions
        merged_layout = {**system_layout, **game_layout}

        style = cfg.layout_style
        template = _STYLE_TEMPLATES.get(style, {})

        display = cfg.display
        button_color = display.get("button_color", "#e63946")

        button_list: List[ButtonInfo] = []
        seen_positions: Dict[Tuple[int, int], bool] = {}

        for btn_id, label in labels.items():
            if btn_id in merged_layout:
                pos = merged_layout[btn_id]
                col, row = int(pos[0]), int(pos[1])
            elif btn_id in template:
                col, row = template[btn_id]
            else:
                idx = len(button_list)
                col, row = idx % 4, idx // 4

            while (col, row) in seen_positions:
                col += 1

            seen_positions[(col, row)] = True

            is_axis = "JOYSTICK" in btn_id or btn_id in (
                "UP", "DOWN", "LEFT", "RIGHT",
                "JOYSTICK_LEFT_UP", "JOYSTICK_LEFT_DOWN",
                "JOYSTICK_LEFT_LEFT", "JOYSTICK_LEFT_RIGHT",
            )

            button_list.append(ButtonInfo(
                id=btn_id,
                label=label,
                col=col,
                row=row,
                color=button_color,
                is_axis=is_axis,
            ))

        button_list.sort(key=lambda b: (b.row, b.col))

        # Resolve game title from mame.dat if available and no toml override
        game_name = cfg.game_name
        if (
            cfg.system == "mame"
            and cfg.game
            and not cfg._game_cfg.get("game", {}).get("name")
            and cfg.mame_dat_path
        ):
            info = mame_dat_lookup(cfg.game, cfg.mame_dat_path)
            if info:
                game_name = info.description

        return LayoutResult(
            system_name=cfg.system_name,
            game_name=game_name,
            style=style,
            buttons=button_list,
            logo_path=cfg.logo_path,
            background_path=cfg.background_path,
            panel_color=display.get("panel_color", "#0d0d0d"),
            button_color=button_color,
            button_label_color=display.get("button_label_color", "#ffffff"),
            button_border_color=display.get("button_border_color", "#ff6b6b"),
            stick_color=display.get("stick_color", "#2b2d42"),
        )