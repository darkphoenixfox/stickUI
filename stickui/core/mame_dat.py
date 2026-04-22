"""
stickui.core.mame_dat
~~~~~~~~~~~~~~~~~~~~~
Reads MAME's XML data file (mame.dat or mame.xml) to resolve
a ROM name to its full arcade title, year and manufacturer.

The file can be very large (500MB+) so we use iterative XML parsing
(xml.etree.ElementTree.iterparse) to avoid loading it all into memory.
Results are cached in memory for the session.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MachineInfo:
    name:         str
    description:  str
    year:         str
    manufacturer: str


# Session cache — populated on first lookup per dat file
_cache: dict[str, dict[str, MachineInfo]] = {}


def _load(dat_path: Path) -> dict[str, MachineInfo]:
    """Parse the dat file and return a {rom_name: MachineInfo} dict."""
    key = str(dat_path)
    if key in _cache:
        return _cache[key]

    result: dict[str, MachineInfo] = {}

    try:
        for event, elem in ET.iterparse(str(dat_path), events=("end",)):
            if elem.tag == "machine":
                name = elem.get("name", "")
                desc = ""
                year = ""
                mfr  = ""

                desc_el = elem.find("description")
                year_el = elem.find("year")
                mfr_el  = elem.find("manufacturer")

                if desc_el is not None and desc_el.text:
                    desc = desc_el.text.strip()
                if year_el is not None and year_el.text:
                    year = year_el.text.strip()
                if mfr_el is not None and mfr_el.text:
                    mfr = mfr_el.text.strip()

                if name:
                    result[name] = MachineInfo(
                        name=name,
                        description=desc,
                        year=year,
                        manufacturer=mfr,
                    )

                # Free memory as we go
                elem.clear()
    except Exception as e:
        print(f"[stickui] mame.dat parse error: {e}")

    _cache[key] = result
    return result


def lookup(rom_name: str, dat_path: Path) -> Optional[MachineInfo]:
    """
    Return MachineInfo for *rom_name* from *dat_path*, or None if not found.
    Results are cached — subsequent calls for the same file are instant.
    """
    if not dat_path or not dat_path.is_file():
        return None
    db = _load(dat_path)
    return db.get(rom_name)