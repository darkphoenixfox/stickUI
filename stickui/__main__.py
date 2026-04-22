#!/usr/bin/env python3
"""
stickui – Controller button layout overlay

Usage
-----
  python -m stickui --system snes
  python -m stickui --system mame --game sf2
  python -m stickui --system snes --stick myStick --width 700 --height 300

The UI reloads automatically when any config file is saved.
Right-click → Reload Now to force an immediate refresh.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from stickui.core.config import ConfigLoader
from stickui.core.layout import LayoutResolver
from stickui.core.stick import load_stick_layout
from stickui.ui.window import OverlayWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="stickui")
    parser.add_argument("--system", required=True)
    parser.add_argument("--game",   default=None)
    parser.add_argument("--stick",  default=None)
    parser.add_argument("--xpos",   type=int, default=None)
    parser.add_argument("--ypos",   type=int, default=None)
    parser.add_argument("--width",  type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    return parser.parse_args()


def build(args: argparse.Namespace, cli_args: dict):
    """Parse all configs and return (cfg, layout, stick_layout)."""
    cfg = ConfigLoader(system=args.system, game=args.game, cli_args=cli_args)
    layout = LayoutResolver(cfg).resolve()

    stick_name = (
        args.stick
        or cfg._system_cfg.get("system", {}).get("stick", "default")
    )
    stick_layout = load_stick_layout(
        stick_name = stick_name,
        sticks_dir = Path("sticks"),
        system_cfg = cfg._system_cfg,
        game_cfg   = cfg._game_cfg,
    )
    return cfg, layout, stick_layout


def main() -> None:
    args = parse_args()
    cli_args = {k: getattr(args, k) for k in ("xpos", "ypos", "width", "height")}

    app = QApplication(sys.argv)
    app.setApplicationName("StickUI")

    cfg, layout, stick_layout = build(args, cli_args)
    win_cfg = cfg.window

    window = OverlayWindow(
        layout_result     = layout,
        cfg               = cfg,
        stick_layout      = stick_layout,
        reload_callback   = None,          # set below after window exists
        x                 = win_cfg.get("xpos",   100),
        y                 = win_cfg.get("ypos",   100),
        width             = win_cfg.get("width",  620),
        height            = win_cfg.get("height", 280),
        opacity           = win_cfg.get("opacity", 0.92),
        auto_hide_seconds = win_cfg.get("auto_hide_seconds", 0),
    )

    def reload():
        """Re-parse all configs and update the window in place."""
        try:
            new_cfg, new_layout, new_stick = build(args, cli_args)
            window.reload(new_layout, new_cfg, new_stick)
        except Exception as e:
            print(f"[stickui] Reload error: {e}")

    window._reload_callback = reload

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()