"""
stickui.ui.settings_dialog
~~~~~~~~~~~~~~~~~~~~~~~~~~
Settings dialog with sliders for opacity and spinboxes for position/size.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QSlider, QSpinBox,
    QVBoxLayout, QWidget,
)
from PyQt6.QtGui import QFont

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


# ---------------------------------------------------------------------------
# TOML helpers
# ---------------------------------------------------------------------------

def _load_toml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open("rb") as f:
        try:
            return tomllib.load(f)
        except Exception:
            return {}


def _save_toml(path: Path, data: dict) -> None:
    if _HAS_TOMLI_W:
        with path.open("wb") as f:
            tomli_w.dump(data, f)
        return

    # Fallback: patch [general] section line by line
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        general = data.get("general", {})
        keys = {"xpos", "ypos", "width", "height", "opacity", "auto_hide_seconds"}
        in_general = False
        out = []
        for line in lines:
            s = line.strip()
            if s == "[general]":
                in_general = True
                out.append(line)
                continue
            if s.startswith("[") and s != "[general]":
                in_general = False
            if in_general:
                for key in keys:
                    if s.startswith(key + " ") or s.startswith(key + "="):
                        val = general.get(key)
                        if isinstance(val, float):
                            line = f"{key} = {val:.2f}\n"
                        else:
                            line = f"{key} = {val}\n"
                        break
            out.append(line)
        path.write_text("".join(out), encoding="utf-8")
    except Exception as e:
        print(f"[stickui] Could not save config: {e}")


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_STYLE = """
QDialog {
    background: #16162a;
    color: #e0e0e0;
}
QGroupBox {
    color: #9090b8;
    font-weight: bold;
    font-size: 11px;
    border: 1px solid #2a2a50;
    border-radius: 8px;
    margin-top: 10px;
    padding: 10px 8px 8px 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QLabel {
    color: #b0b0cc;
    font-size: 12px;
    background: transparent;
}
QLabel#value_label {
    color: #ffffff;
    font-weight: bold;
    min-width: 38px;
}
QSpinBox {
    background: #0e0e20;
    color: #e0e0e0;
    border: 1px solid #2a2a50;
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 12px;
    min-width: 70px;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 18px;
    background: #22224a;
    border-left: 1px solid #2a2a50;
}
QSpinBox::up-arrow   { image: none; width: 6px; height: 6px; }
QSpinBox::down-arrow { image: none; width: 6px; height: 6px; }
QSlider::groove:horizontal {
    height: 4px;
    background: #2a2a50;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #6644cc;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #6644cc;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #ccaaff;
}
QCheckBox {
    color: #b0b0cc;
    font-size: 12px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #444466;
    border-radius: 4px;
    background: #0e0e20;
}
QCheckBox::indicator:checked {
    background: #6644cc;
    border-color: #9977ff;
}
QPushButton {
    background: #22224a;
    color: #d0d0e8;
    border: 1px solid #333366;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 12px;
}
QPushButton:hover   { background: #2e2e60; border-color: #5544aa; }
QPushButton:pressed { background: #6644cc; }
QPushButton#primaryBtn {
    background: #6644cc;
    color: #ffffff;
    border-color: #9977ff;
    font-weight: bold;
    padding: 8px 20px;
}
QPushButton#primaryBtn:hover { background: #7755dd; }
"""


# ---------------------------------------------------------------------------
# Reusable slider row widget
# ---------------------------------------------------------------------------

class SliderRow(QWidget):
    """
    A labelled horizontal slider with a live value readout.
      label     – left label text
      min_val   – minimum value (int, scaled by *scale*)
      max_val   – maximum value (int, scaled by *scale*)
      value     – initial real value
      scale     – divide slider int by this to get real value  (e.g. 100 → 0.01 steps)
      suffix    – appended to the readout label (e.g. "%", "s")
      fmt       – format string for the readout  (e.g. "{:.0f}", "{:.2f}")
    """

    def __init__(
        self,
        label: str,
        min_val: int,
        max_val: int,
        value: float,
        scale: int = 1,
        suffix: str = "",
        fmt: str = "{:.0f}",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._scale  = scale
        self._suffix = suffix
        self._fmt    = fmt

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        lbl = QLabel(label)
        lbl.setFixedWidth(70)
        row.addWidget(lbl)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(min_val, max_val)
        self._slider.setValue(int(round(value * scale)))
        self._slider.setTickInterval((max_val - min_val) // 10)
        row.addWidget(self._slider, stretch=1)

        self._readout = QLabel(self._format(self._slider.value()))
        self._readout.setObjectName("value_label")
        self._readout.setFixedWidth(46)
        self._readout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._readout)

        self._slider.valueChanged.connect(self._on_change)

    def _format(self, raw: int) -> str:
        real = raw / self._scale
        return self._fmt.format(real) + self._suffix

    def _on_change(self, raw: int) -> None:
        self._readout.setText(self._format(raw))

    def value(self) -> float:
        return self._slider.value() / self._scale

    def set_value(self, v: float) -> None:
        self._slider.setValue(int(round(v * self._scale)))


# ---------------------------------------------------------------------------
# Spinbox pair (label + spinbox on one row)
# ---------------------------------------------------------------------------

class SpinRow(QWidget):
    """Label + [−] [value px] [+] row."""

    def __init__(self, label: str, value: int, min_: int, max_: int, suffix: str = "", step: int = 1, parent=None):
        super().__init__(parent)
        self._min = min_
        self._max = max_
        self._step = step

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFixedWidth(70)
        row.addWidget(lbl)

        self._minus = QPushButton("−")
        self._minus.setFixedSize(28, 28)
        self._minus.setStyleSheet(
            "QPushButton { background:#22224a; border:1px solid #333366;"
            "border-radius:5px; font-size:16px; font-weight:bold; color:#ccccee; }"
            "QPushButton:hover { background:#3a3a6a; }"
            "QPushButton:pressed { background:#6644cc; }"
        )
        row.addWidget(self._minus)

        self._spin = QSpinBox()
        self._spin.setRange(min_, max_)
        self._spin.setValue(value)
        self._spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if suffix:
            self._spin.setSuffix(f" {suffix}")
        row.addWidget(self._spin, stretch=1)

        self._plus = QPushButton("+")
        self._plus.setFixedSize(28, 28)
        self._plus.setStyleSheet(
            "QPushButton { background:#22224a; border:1px solid #333366;"
            "border-radius:5px; font-size:16px; font-weight:bold; color:#ccccee; }"
            "QPushButton:hover { background:#3a3a6a; }"
            "QPushButton:pressed { background:#6644cc; }"
        )
        row.addWidget(self._plus)

        self._minus.clicked.connect(lambda: self._increment(-1))
        self._plus.clicked.connect(lambda: self._increment(1))

    def _increment(self, delta: int) -> None:
        self._spin.setValue(max(self._min, min(self._max, self._spin.value() + delta * self._step)))

    def value(self) -> int:
        return self._spin.value()

    def set_value(self, v: int) -> None:
        self._spin.setValue(v)


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):

    def __init__(
        self,
        config_path: Path,
        current_geometry,       # QRect
        current_opacity: float,
        on_apply: Callable[[dict], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._config_path    = config_path
        self._on_apply       = on_apply
        self._live_geometry  = current_geometry

        self.setWindowTitle("StickUI – Settings")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(_STYLE)
        self.setFixedWidth(380)

        saved = _load_toml(config_path).get("general", {})
        g     = current_geometry

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(18, 18, 18, 18)

        # Title
        title = QLabel("Settings")
        title.setFont(QFont("sans-serif", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff; background: transparent;")
        root.addWidget(title)

        # ── Position & Size ─────────────────────────────────────────────────
        pos_box = QGroupBox("Position && Size")
        pv = QVBoxLayout(pos_box)
        pv.setSpacing(8)

        self._xpos   = SpinRow("X",      saved.get("xpos",   g.x()),      -9999, 9999, "px", step=10)
        self._ypos   = SpinRow("Y",      saved.get("ypos",   g.y()),      -9999, 9999, "px", step=10)
        self._width  = SpinRow("Width",  saved.get("width",  g.width()),    100,  3840, "px", step=10)
        self._height = SpinRow("Height", saved.get("height", g.height()),    80,  2160, "px", step=10)

        for w in (self._xpos, self._ypos, self._width, self._height):
            pv.addWidget(w)

        capture_btn = QPushButton("📍  Capture Current Position && Size")
        capture_btn.clicked.connect(self._capture)
        pv.addWidget(capture_btn)
        root.addWidget(pos_box)

        # ── Appearance ──────────────────────────────────────────────────────
        appear_box = QGroupBox("Appearance")
        av = QVBoxLayout(appear_box)
        av.setSpacing(10)

        self._opacity = SliderRow(
            label="Opacity",
            min_val=5, max_val=100,
            value=round(saved.get("opacity", current_opacity) * 100),
            scale=1,
            suffix="%",
            fmt="{:.0f}",
        )
        av.addWidget(self._opacity)
        root.addWidget(appear_box)

        # ── Auto-hide ───────────────────────────────────────────────────────
        hide_box = QGroupBox("Auto-hide")
        hv = QVBoxLayout(hide_box)
        hv.setSpacing(10)

        saved_secs = int(saved.get("auto_hide_seconds", 0))
        self._autohide_cb = QCheckBox("Hide window after inactivity")
        self._autohide_cb.setChecked(saved_secs > 0)
        hv.addWidget(self._autohide_cb)

        self._autohide_secs = SliderRow(
            label="Delay",
            min_val=1, max_val=120,
            value=max(saved_secs, 5),
            scale=1,
            suffix="s",
            fmt="{:.0f}",
        )
        self._autohide_secs.setEnabled(saved_secs > 0)
        self._autohide_cb.toggled.connect(self._autohide_secs.setEnabled)
        hv.addWidget(self._autohide_secs)
        root.addWidget(hide_box)

        # ── Buttons ─────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        apply_btn = QPushButton("Apply && Save")
        apply_btn.setObjectName("primaryBtn")
        apply_btn.clicked.connect(self._apply)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(apply_btn)
        root.addLayout(btn_row)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _capture(self) -> None:
        g = self._live_geometry
        self._xpos.set_value(g.x())
        self._ypos.set_value(g.y())
        self._width.set_value(g.width())
        self._height.set_value(g.height())

    def _collect(self) -> dict:
        return {
            "xpos":              self._xpos.value(),
            "ypos":              self._ypos.value(),
            "width":             self._width.value(),
            "height":            self._height.value(),
            "opacity":           round(self._opacity.value() / 100, 2),
            "auto_hide_seconds": (
                int(self._autohide_secs.value())
                if self._autohide_cb.isChecked() else 0
            ),
        }

    def _apply(self) -> None:
        values = self._collect()
        raw = _load_toml(self._config_path)
        raw.setdefault("general", {}).update(values)
        _save_toml(self._config_path, raw)
        self._on_apply(values)
        self.accept()