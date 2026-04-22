"""
stickui.core.launchbox
~~~~~~~~~~~~~~~~~~~~~~
LaunchBox integration — resolves game titles, regions, logos and
backgrounds from a LaunchBox installation.

Folder layout assumed:
  <launchbox_dir>/
    LaunchBox.exe
    Data/
      Platforms/
        Arcade.xml
        Super Nintendo Entertainment System.xml
    Images/
      Arcade/
        Clear Logo/
          World/
            Final Fight-01.png
        Fanart - Background/
          World/
            Final Fight-01.png
      Super Nintendo Entertainment System/
        Clear Logo/
          ...
        Fanart - Background/
          ...

Usage in system.toml:
  [system]
  launchbox_dir    = 'D:/LaunchBox'
  launchbox_platform = 'Arcade'    # must match the XML filename (without .xml)

  # short_name is used for --system flag (see below)
  short_name = 'mame'
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class LBGame:
    rom_name:  str      # stem of ApplicationPath (e.g. "ffight")
    title:     str      # <Title>
    region:    str      # <Region>
    platform:  str      # <Platform>


# Session cache {xml_path: {rom_name: LBGame}}
_xml_cache: dict[str, dict[str, LBGame]] = {}


# ---------------------------------------------------------------------------
# XML parser
# ---------------------------------------------------------------------------

def _parse_platform_xml(xml_path: Path) -> dict[str, LBGame]:
    key = str(xml_path)
    if key in _xml_cache:
        return _xml_cache[key]

    result: dict[str, LBGame] = {}

    try:
        tree = ET.parse(str(xml_path))
        for game_el in tree.getroot().iter("Game"):
            app_path = game_el.findtext("ApplicationPath", "")
            title    = game_el.findtext("Title",    "")
            region   = game_el.findtext("Region",   "")
            platform = game_el.findtext("Platform", "")

            if not app_path:
                continue

            # ROM name = stem of the ApplicationPath filename
            rom_name = Path(app_path).stem

            result[rom_name] = LBGame(
                rom_name = rom_name,
                title    = title,
                region   = region,
                platform = platform,
            )
    except Exception as e:
        print(f"[stickui] LaunchBox XML parse error ({xml_path.name}): {e}")

    _xml_cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class LaunchBoxDB:
    """
    Wraps a LaunchBox installation and provides asset lookups.

    Parameters
    ----------
    launchbox_dir      : Path to the LaunchBox root (contains LaunchBox.exe)
    launchbox_platform : Platform name matching the XML filename,
                         e.g. "Arcade" or "Super Nintendo Entertainment System"
    """

    def __init__(self, launchbox_dir: str | Path, launchbox_platform: str) -> None:
        self.root     = Path(launchbox_dir).expanduser()
        self.platform = launchbox_platform
        self._valid   = (self.root / "LaunchBox.exe").is_file()
        self._db: dict[str, LBGame] = {}

        if self._valid:
            xml_path = self.root / "Data" / "Platforms" / f"{launchbox_platform}.xml"
            if xml_path.is_file():
                self._db = _parse_platform_xml(xml_path)
            else:
                print(f"[stickui] LaunchBox XML not found: {xml_path}")

    @property
    def valid(self) -> bool:
        return self._valid

    def game_info(self, rom_name: str) -> Optional[LBGame]:
        # Exact match first
        game = self._db.get(rom_name)
        if game:
            return game
        # Case-insensitive fallback
        rom_lower = rom_name.lower()
        for key, val in self._db.items():
            if key.lower() == rom_lower:
                return val
        return None

    @staticmethod
    def _safe_filename(title: str) -> str:
        """
        Convert a game title to its LaunchBox-safe filename equivalent.
        LaunchBox replaces characters illegal in filenames with underscores.
        Illegal chars on Windows: colon, slash, backslash, asterisk, etc.
        e.g. "Street Fighter II: The World Warrior"
          -> "Street Fighter II_ The World Warrior"
        """
        import re
        return re.sub(r'[:/\\*?"<>|]', '_', title)

    def _find_image(
        self,
        category: str,
        title: str,
        region: str,
    ) -> Optional[Path]:
        """
        Search for an image file in:
          <root>/Images/<platform>/<category>/<region>/<safe_title>-01.png
          <root>/Images/<platform>/<category>/<region>/<safe_title>-02.png
          <root>/Images/<platform>/<category>/**/<safe_title>-01.png

        LaunchBox replaces : and other illegal chars with _ in filenames.
        Falls back to searching all subfolders if region-specific not found.
        """
        base = self.root / "Images" / self.platform / category
        if not base.is_dir():
            return None

        exts  = [".png", ".jpg", ".jpeg"]
        safe  = self._safe_filename(title)

        # Build candidate stems: safe title with -01, -02, and bare
        stems_lower = {
            f"{safe}-01".lower(),
            f"{safe}-02".lower(),
            safe.lower(),
            # Also try original title in case filesystem allows it
            f"{title}-01".lower(),
            f"{title}-02".lower(),
            title.lower(),
        }

        # Search order:
        #   1. Root of category folder (no subfolder)
        #   2. World
        #   3. Region from XML (e.g. Europe)
        #   4. North America
        #   5. Any remaining subfolders (alphabetical)
        # This gives predictable precedence regardless of what the XML says.

        def _scan(folder: Path) -> Optional[Path]:
            if not folder.is_dir():
                return None
            for p in sorted(folder.iterdir()):
                if p.is_file() and p.suffix.lower() in exts:
                    if p.stem.lower() in stems_lower:
                        return p
            return None

        # 1. Root (images placed directly in the category folder)
        result = _scan(base)
        if result:
            return result

        # 2. World
        result = _scan(base / "World")
        if result:
            return result

        # 3. Region from XML (skip if same as World or already tried)
        if region and region not in ("World",):
            result = _scan(base / region)
            if result:
                return result

        # 4. North America
        result = _scan(base / "North America")
        if result:
            return result

        # 5. Any other subfolders not yet tried
        tried = {"World", region or "", "North America", ""}
        for sub in sorted(base.iterdir()):
            if sub.is_dir() and sub.name not in tried:
                result = _scan(sub)
                if result:
                    return result

        return None

    def logo(self, rom_name: str) -> Optional[Path]:
        """Return the Clear Logo image path for a ROM, or None."""
        game = self.game_info(rom_name)
        if not game:
            return None
        return self._find_image("Clear Logo", game.title, game.region)

    def background(self, rom_name: str) -> Optional[Path]:
        """Return the Fanart Background image path for a ROM, or None."""
        game = self.game_info(rom_name)
        if not game:
            return None
        return self._find_image("Fanart - Background", game.title, game.region)

    def title(self, rom_name: str) -> Optional[str]:
        """Return the full game title from LaunchBox XML."""
        game = self.game_info(rom_name)
        return game.title if game else None


# ---------------------------------------------------------------------------
# Helper: build from system config
# ---------------------------------------------------------------------------

def from_system_cfg(
    system_cfg: dict,
    global_launchbox_dir: "Path | str | None" = None,
) -> Optional[LaunchBoxDB]:
    """
    Build a LaunchBoxDB from config.

    launchbox_dir priority:
      1. system.toml [system] launchbox_dir  (per-system override)
      2. global config.toml [paths] launchbox_dir

    launchbox_platform must be set in system.toml [system].
    Returns None if not configured or directory invalid.
    """
    sys_sec = system_cfg.get("system", {})

    # Platform is always per-system
    lb_plat = sys_sec.get("launchbox_platform", "")
    if not lb_plat:
        return None

    # Directory: system override > global config
    lb_dir = sys_sec.get("launchbox_dir", "") or str(global_launchbox_dir or "")
    if not lb_dir:
        return None

    db = LaunchBoxDB(lb_dir, lb_plat)
    return db if db.valid else None