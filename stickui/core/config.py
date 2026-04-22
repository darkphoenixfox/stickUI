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

        self.system_dir = self._resolve_system_dir()

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

    def _resolve_system_dir(self) -> Path:
        """
        Find the system folder. Checks:
          1. Exact match: systems_dir / system  (e.g. systems/mame)
          2. short_name match: scan all subfolders for system.toml with
             [system] short_name = "<system>"
        """
        exact = self.systems_dir / self.system
        if exact.is_dir():
            return exact

        # Scan for short_name match
        if self.systems_dir.is_dir():
            for subdir in self.systems_dir.iterdir():
                if not subdir.is_dir():
                    continue
                toml_path = subdir / "system.toml"
                if not toml_path.is_file():
                    continue
                try:
                    cfg = _load_toml(toml_path)
                    if cfg.get("system", {}).get("short_name", "").lower() == self.system.lower():
                        return subdir
                except Exception:
                    continue

        # Fall back to exact even if it doesn't exist yet
        return exact

    def _resolve_system_dir(self) -> Path:
        """
        Find the system folder by checking each subfolder's system.toml
        for a matching short_name, falling back to direct name match.
        """
        # Direct match first (e.g. --system arcade -> systems/arcade/)
        direct = self.systems_dir / self.system
        if direct.is_dir():
            return direct

        # Search for short_name = "<system>" in any system.toml
        if self.systems_dir.is_dir():
            for toml_path in self.systems_dir.glob("*/system.toml"):
                cfg = _load_toml(toml_path)
                short = cfg.get("system", {}).get("short_name", "")
                if short.lower() == self.system.lower():
                    return toml_path.parent

        # Fallback: return the direct path even if it doesn't exist
        return direct

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
        Logo priority:
          1. systems/<s>/<game>.png  (explicit local override)
          2. LaunchBox Clear Logo    (from launchbox_dir + platform XML)
          3. systems/<s>/logo.png or <s>.png  (system fallback)
        """
        from .launchbox import from_system_cfg

        # 1 — explicit game.toml override
        if self.game:
            game_logo_name = self._game_cfg.get("game", {}).get("logo")
            if game_logo_name:
                p = self.system_dir / game_logo_name
                if p.is_file():
                    return p

        # 1b — <game>.png directly in system folder
        if self.game:
            p = self.system_dir / f"{self.game}.png"
            if p.is_file():
                return p

        # 2 — LaunchBox Clear Logo
        if self.game:
            lb = from_system_cfg(self._system_cfg, self.launchbox_dir)
            if lb:
                p = lb.logo(self.game)
                if p:
                    return p

        # 3 — explicit system logo from system.toml
        sys_logo_name = self._system_cfg.get("system", {}).get("logo")
        if sys_logo_name:
            p = self.system_dir / sys_logo_name
            if p.is_file():
                return p

        # 3b — generic logo.png / <s>.png
        for name in ["logo.png", f"{self.system}.png"]:
            p = self.system_dir / name
            if p.is_file():
                return p

        return None


    @property
    def background_path(self) -> Path | None:
        """
        Background priority:
          1. game.toml [game] background (explicit)
          2. <game>_bg.png/jpg in system folder
          3. LaunchBox Fanart - Background
          4. system.toml [system] background / background.png/jpg
          5. gradient fallback (handled in UI)
        """
        from .launchbox import from_system_cfg

        exts = [".png", ".jpg", ".jpeg"]

        def _find(name: str | None, *fallback_stems: str) -> Path | None:
            candidates = []
            if name:
                candidates.append(self.system_dir / name)
            for stem in fallback_stems:
                for ext in exts:
                    candidates.append(self.system_dir / f"{stem}{ext}")
            for p in candidates:
                if p.is_file():
                    return p
            return None

        # 1 & 2 — game-level
        if self.game:
            bg_name = self._game_cfg.get("game", {}).get("background")
            result = _find(bg_name, f"{self.game}_bg")
            if result:
                return result

        # 3 — LaunchBox Fanart Background
        if self.game:
            lb = from_system_cfg(self._system_cfg, self.launchbox_dir)
            if lb:
                p = lb.background(self.game)
                if p:
                    return p

        # 4 — system-level
        sys_bg_name = self._system_cfg.get("system", {}).get("background")
        return _find(sys_bg_name, "background")


    @property
    def system_name(self) -> str:
        return self._system_cfg.get("system", {}).get("name", self.system.upper())

    @property
    def game_name(self) -> str:
        if not self.game:
            return ""
        # Priority: game.toml name > LaunchBox title > rom name
        toml_name = self._game_cfg.get("game", {}).get("name", "")
        if toml_name:
            return toml_name
        try:
            from .launchbox import from_system_cfg
            lb = from_system_cfg(self._system_cfg, self.launchbox_dir)
            if lb:
                lb_title = lb.title(self.game)
                if lb_title:
                    return lb_title
        except Exception:
            pass
        return self.game

    @property
    def layout_style(self) -> str:
        """One of: arcade, gamepad, keyboard, custom."""
        return self.display.get("layout_style", "gamepad")

    @property
    def background_dim(self) -> float:
        """
        Darkening overlay opacity for background images (0.0–1.0).
        Priority: game.toml > system.toml > config.toml > default (0.55)
        """
        # game.toml [display]
        game_val = self._game_cfg.get("display", {}).get("background_dim")
        if game_val is not None:
            return max(0.0, min(1.0, float(game_val)))

        # system.toml [display]
        sys_val = self._system_cfg.get("display", {}).get("background_dim")
        if sys_val is not None:
            return max(0.0, min(1.0, float(sys_val)))

        # config.toml [general]
        global_val = self._global.get("general", {}).get("background_dim")
        if global_val is not None:
            return max(0.0, min(1.0, float(global_val)))

        return 0.55   # default: moderate darkening

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

    @property
    def launchbox_dir(self) -> Path | None:
        """Path to LaunchBox root folder, or None if not configured."""
        val = self._global["paths"].get("launchbox_dir", "")
        if not val:
            return None
        p = Path(val).expanduser()
        return p if p.is_dir() else None

    @property
    def launchbox_platform(self):
        """
        Return a LaunchBoxPlatform if launchbox_folder is set and valid,
        else None. Result is cached on the instance.
        """
        if hasattr(self, "_lb_platform_cache"):
            return self._lb_platform_cache

        lb_str = self._system_cfg.get("system", {}).get("launchbox_folder", "")
        if not lb_str:
            self._lb_platform_cache = None
            return None

        lb_folder = Path(lb_str).expanduser()
        try:
            from .launchbox import is_valid_launchbox, load_platform
            if not is_valid_launchbox(lb_folder):
                self._lb_platform_cache = None
                return None
            platform_name = self._system_cfg.get("system", {}).get(
                "launchbox_platform",
                self._system_cfg.get("system", {}).get("name", self.system)
            )
            self._lb_platform_cache = load_platform(lb_folder, platform_name)
        except Exception as e:
            print(f"[stickui] LaunchBox error: {e}")
            self._lb_platform_cache = None

        return self._lb_platform_cache