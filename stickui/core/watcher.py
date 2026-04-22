"""
stickui.core.watcher
~~~~~~~~~~~~~~~~~~~~
Watches config files for changes and emits a Qt signal when any of them
are modified. Uses QFileSystemWatcher (no extra dependencies).

Files watched:
  - config.toml
  - systems/<s>/system.toml
  - systems/<s>/<game>.toml   (if present)
  - sticks/<n>.toml           (if present)
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from PyQt6.QtCore import QFileSystemWatcher, QObject, pyqtSignal


class ConfigWatcher(QObject):
    """
    Emits `changed` whenever any watched config file is modified.
    """

    changed = pyqtSignal()

    def __init__(self, paths: List[Path], parent=None) -> None:
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self.set_paths(paths)

    def set_paths(self, paths: List[Path]) -> None:
        # Remove existing watched paths
        existing = self._watcher.files()
        if existing:
            self._watcher.removePaths(existing)

        # Add only paths that exist
        valid = [str(p) for p in paths if p.is_file()]
        if valid:
            self._watcher.addPaths(valid)

    def _on_file_changed(self, path: str) -> None:
        # Some editors replace files atomically (delete + write), which
        # removes them from the watcher. Re-add if still present.
        p = Path(path)
        if p.is_file() and path not in self._watcher.files():
            self._watcher.addPath(path)
        self.changed.emit()


def watched_paths(
    config_toml: Path,
    system_toml: Path,
    game_toml: Path | None,
    stick_toml: Path | None,
) -> List[Path]:
    """Return the list of config files that should be watched."""
    paths = [config_toml, system_toml]
    if game_toml:
        paths.append(game_toml)
    if stick_toml:
        paths.append(stick_toml)
    return [p for p in paths if p.is_file()]