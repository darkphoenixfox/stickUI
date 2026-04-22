#!/usr/bin/env python3
"""
controlpad – Controller button layout overlay
=============================================

Usage
-----
  python -m controlpad --system mame --game sf2
  python -m controlpad --system snes --game smw --xpos 50 --ypos 50 --width 900 --height 500

Flags
-----
  --system   Emulator id  (mame, snes, nes, genesis, …)
  --game     ROM name without extension  (sf2, smw, …)
  --xpos     Window X position (overrides config)
  --ypos     Window Y position (overrides config)
  --width    Window width in pixels
  --height   Window height in pixels
  --config   Path to a custom global config.toml
"""

from __future__ import annotations

import argparse
import sys

from PyQt6.QtWidgets import QApplication

from stickui.core.config import ConfigLoader
from stickui.core.layout import LayoutResolver
from stickui.ui.window import OverlayWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="controlpad",
        description="Display a controller button layout overlay.",
    )
    parser.add_argument("--system",  required=True, help="Emulator id (mame, snes, …)")
    parser.add_argument("--game",    default=None,  help="ROM name without extension")
    parser.add_argument("--xpos",   type=int, default=None)
    parser.add_argument("--ypos",   type=int, default=None)
    parser.add_argument("--width",  type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--config", default=None, help="Path to global config.toml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    cli_args = {
        "xpos":   args.xpos,
        "ypos":   args.ypos,
        "width":  args.width,
        "height": args.height,
    }

    # ── Load & merge config ─────────────────────────────────────────────────
    cfg = ConfigLoader(
        system=args.system,
        game=args.game,
        cli_args=cli_args,
    )

    # ── Resolve layout ──────────────────────────────────────────────────────
    resolver = LayoutResolver(cfg)
    layout = resolver.resolve()

    # ── Launch Qt window ────────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("ControlPad")

    win_cfg = cfg.window
    window = OverlayWindow(
        layout_result=layout,
        x=win_cfg.get("xpos", 100),
        y=win_cfg.get("ypos", 100),
        width=win_cfg.get("width", 800),
        height=win_cfg.get("height", 480),
        opacity=win_cfg.get("opacity", 0.92),
        auto_hide_seconds=win_cfg.get("auto_hide_seconds", 0),
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()