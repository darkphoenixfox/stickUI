"""
stickui.core.game_writer
~~~~~~~~~~~~~~~~~~~~~~~~
Serialises the current slot state into a <game>.toml file.

Only values that differ from the system defaults are written,
keeping the file minimal. If the file already exists its [game]
and [display] sections are preserved; only [buttons], [directions]
and [button_colors] are replaced.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .stick import InputSlot, StickLayout

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

try:
    import tomli_w
    _HAS_TOMLI_W = True
except ImportError:
    _HAS_TOMLI_W = False


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as f:
        try:
            return tomllib.load(f)
        except Exception:
            return {}


def _toml_str(value: Any) -> str:
    """Render a Python value as a TOML value string."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _write_manual(path: Path, data: dict) -> None:
    """Hand-roll a TOML file when tomli_w is not available."""
    lines = []

    def _section(name: str, d: dict):
        if not d:
            return
        lines.append(f"\n[{name}]")
        for k, v in d.items():
            if isinstance(v, dict):
                # inline table
                inner = ", ".join(f'{ik} = {_toml_str(iv)}' for ik, iv in v.items())
                lines.append(f'{k} = {{ {inner} }}')
            else:
                lines.append(f'{k} = {_toml_str(v)}')

    # Write each top-level section
    for section, content in data.items():
        if isinstance(content, dict):
            _section(section, content)
        else:
            lines.append(f'{section} = {_toml_str(content)}')

    path.write_text("\n".join(lines).lstrip() + "\n", encoding="utf-8")


def save_game_toml(
    game_toml_path: Path,
    stick_layout: StickLayout,
    system_cfg: dict[str, Any],
    game_cfg: dict[str, Any],
) -> None:
    """
    Write the current stick layout state to <game>.toml.

    Preserves existing [game] and [display] sections.
    Replaces [buttons], [directions], [button_colors].
    Only writes values that differ from system defaults.
    """
    # Start from existing game config to preserve [game] name/logo etc.
    existing = dict(game_cfg)

    sys_btns  = system_cfg.get("buttons", {}) or system_cfg.get("defaults", {}).get("buttons", {})
    sys_dirs  = system_cfg.get("directions", {}) or system_cfg.get("defaults", {}).get("axes", {})
    sys_colors = system_cfg.get("button_colors", {})

    buttons: dict[str, str] = {}
    directions: dict[str, str] = {}
    button_colors: dict[str, dict] = {}

    for slot in stick_layout.directions:
        sys_default = sys_dirs.get(slot.id, slot.id.capitalize())
        label_out = slot.label.replace("\n", "\\n")
        if label_out != sys_default:
            directions[slot.id] = label_out

    for slot in stick_layout.buttons:
        sys_default = sys_btns.get(slot.id, slot.id.upper())
        label_out = slot.label.replace("\n", "\\n")

        # Always write button labels so the file is explicit
        buttons[slot.id] = label_out

        # Write color only if it differs from system default
        sys_color = sys_colors.get(slot.id, {})
        color_changed = (
            slot.color  and slot.color  != sys_color.get("color", "") or
            slot.border and slot.border != sys_color.get("border", "")
        )
        if color_changed and slot.kind == "button":
            entry = {}
            if slot.color:
                entry["color"]  = slot.color
            if slot.border:
                entry["border"] = slot.border
            if entry:
                button_colors[slot.id] = entry

    # Build output dict preserving existing [game] and [display]
    out: dict[str, Any] = {}
    if "game" in existing:
        out["game"] = existing["game"]
    if "display" in existing:
        out["display"] = existing["display"]
    if buttons:
        out["buttons"] = buttons
    if directions:
        out["directions"] = directions
    if button_colors:
        out["button_colors"] = button_colors

    # Write
    game_toml_path.parent.mkdir(parents=True, exist_ok=True)

    if _HAS_TOMLI_W:
        with game_toml_path.open("wb") as f:
            tomli_w.dump(out, f)
    else:
        _write_manual(game_toml_path, out)