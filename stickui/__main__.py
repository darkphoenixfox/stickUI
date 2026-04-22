#!/usr/bin/env python3
"""
stickui – Controller button layout overlay

Usage
-----
  python -m stickui --system snes
  python -m stickui --system mame --game sf2 --stick myStick
  python -m stickui --system snes --xpos 50 --ypos 50 --width 700 --height 300

Flags
-----
  --system   Emulator id  (mame, snes, nes, genesis, …)
  --game     ROM name without extension  (sf2, smw, …)
  --stick    Stick config name in sticks/ folder (default: from system.toml or "default")
  --xpos     Window X position
  --ypos     Window Y position
  --width    Window width in pixels
  --height   Window height in pixels
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
    parser.add_argument("--stick",  default=None,
                        help="Stick config name (sticks/<name>.toml)")
    parser.add_argument("--xpos",   type=int, default=None)
    parser.add_argument("--ypos",   type=int, default=None)
    parser.add_argument("--width",  type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    cli_args = {k: getattr(args, k)
                for k in ("xpos", "ypos", "width", "height")}

    # ── Config ──────────────────────────────────────────────────────────────
    cfg = ConfigLoader(system=args.system, game=args.game, cli_args=cli_args)

    # ── Layout (for colours, logo, background) ──────────────────────────────
    layout = LayoutResolver(cfg).resolve()

    # ── Stick layout ────────────────────────────────────────────────────────
    # Priority: CLI --stick > system.toml [system] stick = "..." > "default"
    stick_name = (
        args.stick
        or cfg._system_cfg.get("system", {}).get("stick", "default")
    )

    # sticks/ folder lives next to config.toml (repo root / cwd)
    sticks_dir = Path("sticks")

    stick_layout = load_stick_layout(
        stick_name  = stick_name,
        sticks_dir  = sticks_dir,
        system_cfg  = cfg._system_cfg,
        game_cfg    = cfg._game_cfg,
    )

    # ── Window ──────────────────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("StickUI")

    win_cfg = cfg.window
    window = OverlayWindow(
        layout_result = layout,
        stick_layout  = stick_layout,
        x             = win_cfg.get("xpos", 100),
        y             = win_cfg.get("ypos", 100),
        width         = win_cfg.get("width", 800),
        height        = win_cfg.get("height", 300),
        opacity       = win_cfg.get("opacity", 0.92),
        auto_hide_seconds = win_cfg.get("auto_hide_seconds", 0),
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()