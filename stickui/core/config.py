"""
controlpad.core.config
~~~~~~~~~~~~~~~~~~~~~~
Loads and merges configuration at three levels:
  1. Global   (~/.config/controlpad/config.toml or ./config.toml)
  2. System   (<systems_dir>/<system>/system.toml)
  3. Game     (<systems_dir>/<system>/<game>.toml)

The result is a single dict that callers can query.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional TOML support – Python 3.11+ ships tomllib; older versions need
# the third-party `tomli` package.
# ---------------------------------------------------------------------------
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib          # type: ignore[no-redef]
    except ImportError:
        try:
            import tomli as tomllib   # type: ignore[no-redef]
        except ImportError:
            raise SystemExit(
                "Python < 3.11 requires the 'tomli' package. "
                "Install it with:  pip install tomli"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_toml(path: Path) -> dict[str, Any]:
    """Read a TOML file; return empty dict if it does not exist."""
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (override wins)."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


# ---------------------------------------------------------------------------
# Default global config (used when no file is present)
# ---------------------------------------------------------------------------

_GLOBAL_DEFAULTS: dict[str, Any] = {
    "general": {
        "xpos": 100,
        "ypos": 100,
        "width": 800,
        "height": 480,
        "opacity": 0.92,
        "auto_hide_seconds": 0,
    },
    "paths": {
        "systems_dir": "~/.config/controlpad/systems",
        "mame_cfg_dir": "~/.mame/cfg",
        "mame_ctrlr_dir": "~/.mame/ctrlr",
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ConfigLoader:
    """
    Resolves and merges config files for a given system + game combination.

    Parameters
    ----------
    system   : str  –  emulator id, e.g. "mame", "snes"
    game     : str  –  ROM name without extension, e.g. "sf2"
    cli_args : dict –  values supplied via CLI flags (highest priority)
    """

    def __init__(
        self,
        system: str,
        game: str | None = None,
        cli_args: dict[str, Any] | None = None,
    ) -> None:
        self.system = system.lower()
        self.game = game.lower() if game else None
        self.cli_args = cli_args or {}

        # Locate global config
        self.global_config_path = self._find_global_config()
        self._global = _deep_merge(_GLOBAL_DEFAULTS, _load_toml(self.global_config_path))

        # Resolve systems directory
        self.systems_dir = Path(
            self._global["paths"].get("systems_dir", "~/.config/controlpad/systems")
        ).expanduser()

        self.system_dir = self.systems_dir / self.system

        # Load layers
        self._system_cfg = _load_toml(self.system_dir / "system.toml")
        self._game_cfg = self._load_game_cfg()

        # Merged result (global → system → game → cli)
        self._merged = _deep_merge(
            _deep_merge(self._global, self._system_cfg),
            self._game_cfg,
        )

        # Apply CLI overrides into the "general" namespace
        for key in ("xpos", "ypos", "width", "height"):
            if self.cli_args.get(key) is not None:
                self._merged.setdefault("general", {})[key] = self.cli_args[key]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_global_config(self) -> Path:
        """Search for config.toml in canonical locations."""
        candidates = [
            Path("config.toml"),                                  # cwd
            Path("~/.config/controlpad/config.toml").expanduser(),
            Path(__file__).parent.parent / "config.toml",         # next to package
        ]
        for p in candidates:
            if p.is_file():
                return p
        # Return a non-existent path – _load_toml handles missing files gracefully
        return Path("~/.config/controlpad/config.toml").expanduser()

    def _load_game_cfg(self) -> dict[str, Any]:
        """Load the per-game TOML if it exists."""
        if not self.game:
            return {}
        game_toml = self.system_dir / f"{self.game}.toml"
        return _load_toml(game_toml)

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Dot-path accessor.  e.g. cfg.get("general", "width")
        """
        node: Any = self._merged
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k, default)
            if node is default:
                return default
        return node

    @property
    def window(self) -> dict[str, Any]:
        return self._merged.get("general", {})

    @property
    def display(self) -> dict[str, Any]:
        return self._merged.get("display", {})

    @property
    def buttons(self) -> dict[str, str]:
        """
        Resolved button labels (game > system defaults > mame cfg fallback).
        Returns a {button_id: label} mapping.
        """
        # Game-level overrides take highest priority
        labels: dict[str, str] = {}

        # Start from system defaults
        sys_defaults = self._system_cfg.get("defaults", {}).get("buttons", {})
        labels.update(sys_defaults)

        # Game-level overrides
        game_buttons = self._game_cfg.get("buttons", {})
        labels.update(game_buttons)

        return labels

    @property
    def axes(self) -> dict[str, str]:
        """Resolved axis/directional labels."""
        labels: dict[str, str] = {}
        sys_axes = self._system_cfg.get("defaults", {}).get("axes", {})
        labels.update(sys_axes)
        game_axes = self._game_cfg.get("axes", {})
        labels.update(game_axes)
        return labels

    @property
    def layout_positions(self) -> dict[str, list[int]]:
        """Optional per-game button layout grid positions."""
        return self._game_cfg.get("layout", {})

    @property
    def system_dir_path(self) -> Path:
        return self.system_dir

    @property
    def logo_path(self) -> Path | None:
        """
        Returns the best available logo path.

        Priority:
          1. game.toml [game] logo = "..."  (explicit override)
          2. logos_dir recursive search: <game>.png / <game>-01.png
             (Launchbox naming, under system.toml [system] logos_dir)
          3. <game>.png in the system folder
          4. system.toml [system] logo = "..."
          5. logo.png in the system folder
          6. <s>.png (e.g. mame.png, snes.png)
        """
        # 1 — explicit game.toml override
        if self.game:
            game_logo_name = self._game_cfg.get("game", {}).get("logo")
            if game_logo_name:
                p = self.system_dir / game_logo_name
                if p.is_file():
                    return p

        # 2 — logos_dir recursive search (Launchbox style)
        if self.game:
            logos_dir_str = self._system_cfg.get("system", {}).get("logos_dir", "")
            if logos_dir_str:
                logos_dir = Path(logos_dir_str).expanduser()
                if logos_dir.is_dir():
                    stems_lower = {
                        self.game.lower(),
                        f"{self.game.lower()}-01",
                        f"{self.game.lower()}-02",
                    }
                    exts = {".png", ".jpg", ".jpeg"}
                    for p in sorted(logos_dir.rglob("*")):
                        if p.is_file() and p.suffix.lower() in exts:
                            if p.stem.lower() in stems_lower:
                                return p

        # 3 — <game>.png in system folder
        if self.game:
            p = self.system_dir / f"{self.game}.png"
            if p.is_file():
                return p

        # 4 — explicit system logo
        sys_logo_name = self._system_cfg.get("system", {}).get("logo")
        if sys_logo_name:
            p = self.system_dir / sys_logo_name
            if p.is_file():
                return p

        # 5 — generic logo.png
        p = self.system_dir / "logo.png"
        if p.is_file():
            return p

        # 6 — <s>.png (e.g. mame.png, snes.png)
        p = self.system_dir / f"{self.system}.png"
        if p.is_file():
            return p

        return None

    @property
    def background_path(self) -> Path | None:
        """
        Returns background image path (game bg > system bg > None).
        Supports .png, .jpg, .jpeg — explicit config value is tried first,
        then each extension is tried automatically if no config value given.
        """
        _exts = (".png", ".jpg", ".jpeg")

        def _find(name: str | None, stem: str) -> Path | None:
            """Try explicit name first, then stem + each extension."""
            if name:
                p = self.system_dir / name
                if p.is_file():
                    return p
            for ext in _exts:
                p = self.system_dir / (stem + ext)
                if p.is_file():
                    return p
            return None

        # Game-level background
        if self.game:
            bg_name = self._game_cfg.get("game", {}).get("background")
            result = _find(bg_name, f"{self.game}_bg") or _find(bg_name, "background")
            if result:
                return result

        # System-level background
        sys_bg_name = self._system_cfg.get("system", {}).get("background")
        return _find(sys_bg_name, "background")

    @property
    def system_name(self) -> str:
        return self._system_cfg.get("system", {}).get("name", self.system.upper())

    @property
    def game_name(self) -> str:
        if self.game:
            return self._game_cfg.get("game", {}).get("name", self.game)
        return ""

    @property
    def layout_style(self) -> str:
        """One of: arcade, gamepad, keyboard, custom."""
        return self.display.get("layout_style", "gamepad")

    @property
    def mame_cfg_dir(self) -> Path:
        return Path(
            self._global["paths"].get("mame_cfg_dir", "~/.mame/cfg")
        ).expanduser()

    @property
    def mame_dat_path(self) -> Path | None:
        """Path to mame.dat / mame.xml, or None if not configured."""
        val = self._global["paths"].get("mame_dat", "")
        if not val:
            return None
        p = Path(val).expanduser()
        return p if p.is_file() else None

    @property
    def command_dat_path(self) -> Path | None:
        """Path to command.dat, or None if not configured."""
        val = self._global["paths"].get("command_dat", "")
        if not val:
            return None
        p = Path(val).expanduser()
        return p if p.is_file() else None