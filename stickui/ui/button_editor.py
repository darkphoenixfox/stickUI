"""
stickui.ui.button_editor
~~~~~~~~~~~~~~~~~~~~~~~~
Dialog for editing a single button or direction slot in edit mode.
Allows changing label, size, X/Y position, and colour.
Changes are applied live to the slot object; the caller decides when to save.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QColorDialog, QDialog, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from ..core.stick import InputSlot


_STYLE = """
QDialog {
    background: #16162a;
    color: #e0e0e0;
}
QLabel {
    color: #b0b0cc;
    font-size: 12px;
    background: transparent;
}
QLabel#title {
    color: #ffffff;
    font-size: 14px;
    font-weight: bold;
}
QLabel#hint {
    color: rgba(150,150,180,0.7);
    font-size: 10px;
}
QLineEdit {
    background: #0e0e20;
    color: #e0e0e0;
    border: 1px solid #2a2a50;
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 12px;
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
QPushButton {
    background: #22224a;
    color: #d0d0e8;
    border: 1px solid #333366;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 12px;
}
QPushButton:hover   { background: #2e2e60; }
QPushButton:pressed { background: #6644cc; }
QPushButton#applyBtn {
    background: #6644cc;
    color: #fff;
    border-color: #9977ff;
    font-weight: bold;
}
QPushButton#applyBtn:hover { background: #7755dd; }
QPushButton#colorBtn {
    min-width: 80px;
    border-radius: 5px;
    border: 2px solid #555577;
}
"""


class _SpinRow(QWidget):
    def __init__(self, label: str, value: int, min_: int, max_: int, step: int = 1):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        lbl = QLabel(label)
        lbl.setFixedWidth(60)
        row.addWidget(lbl)

        self._minus = QPushButton("−")
        self._minus.setFixedSize(26, 26)
        self._minus.setStyleSheet(
            "QPushButton{background:#22224a;border:1px solid #333366;border-radius:4px;"
            "font-size:15px;font-weight:bold;color:#ccccee;}"
            "QPushButton:hover{background:#3a3a6a;}"
        )
        row.addWidget(self._minus)

        self._spin = QSpinBox()
        self._spin.setRange(min_, max_)
        self._spin.setValue(value)
        self._spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self._spin, stretch=1)

        self._plus = QPushButton("+")
        self._plus.setFixedSize(26, 26)
        self._plus.setStyleSheet(
            "QPushButton{background:#22224a;border:1px solid #333366;border-radius:4px;"
            "font-size:15px;font-weight:bold;color:#ccccee;}"
            "QPushButton:hover{background:#3a3a6a;}"
        )
        row.addWidget(self._plus)

        self._step = step
        self._minus.clicked.connect(lambda: self._increment(-1))
        self._plus.clicked.connect(lambda: self._increment(1))

    def _increment(self, d: int):
        self._spin.setValue(
            max(self._spin.minimum(),
                min(self._spin.maximum(), self._spin.value() + d * self._step))
        )

    def value(self) -> int:
        return self._spin.value()

    def set_value(self, v: int):
        self._spin.setValue(v)


class _ColorRow(QWidget):
    def __init__(self, label: str, color: str):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        self._color = color or "#888888"
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFixedWidth(60)
        row.addWidget(lbl)

        self._btn = QPushButton()
        self._btn.setObjectName("colorBtn")
        self._btn.setFixedHeight(28)
        self._update_swatch()
        self._btn.clicked.connect(self._pick)
        row.addWidget(self._btn, stretch=1)

    def _update_swatch(self):
        self._btn.setText(self._color)
        self._btn.setStyleSheet(
            f"QPushButton#colorBtn {{ background: {self._color}; "
            f"color: {'#fff' if QColor(self._color).lightness() < 128 else '#000'}; "
            f"border: 2px solid #555577; border-radius: 5px; font-size: 11px; }}"
        )

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._color), self, "Pick colour")
        if c.isValid():
            self._color = c.name()
            self._update_swatch()

    def value(self) -> str:
        return self._color


class _CachePreview(QWidget):
    """
    Small widget showing the cached style:
      [NNpx]  [■ fill colour]  [■ border colour]
    Invisible when cache is empty.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self._size   = 0
        self._color  = ""
        self._border = ""
        self.setMinimumWidth(10)

    def update_cache(self, cache: dict) -> None:
        self._size   = cache.get("size",   0)
        self._color  = cache.get("color",  "")
        self._border = cache.get("border", "")
        self.setVisible(bool(cache))
        self.update()

    def paintEvent(self, event):
        if not self._size and not self._color:
            return
        from PyQt6.QtGui import QPainter, QColor, QFont
        from PyQt6.QtCore import QRect, Qt
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        x = 0
        y = (self.height() - 16) // 2

        # Size pill
        size_text = f"{self._size}px"
        p.setFont(QFont("sans-serif", 8, QFont.Weight.Bold))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(size_text) + 8
        p.setBrush(QColor(40, 40, 70))
        p.setPen(QColor(80, 80, 120))
        p.drawRoundedRect(x, y, tw, 16, 4, 4)
        p.setPen(QColor(180, 180, 220))
        p.drawText(QRect(x, y, tw, 16), Qt.AlignmentFlag.AlignCenter, size_text)
        x += tw + 4

        # Fill colour swatch
        if self._color:
            p.setPen(QColor(80, 80, 80))
            p.setBrush(QColor(self._color))
            p.drawRoundedRect(x, y, 16, 16, 3, 3)
            x += 20

        # Border colour swatch
        if self._border:
            p.setPen(QColor(80, 80, 80))
            p.setBrush(QColor(self._border))
            p.drawRoundedRect(x, y, 16, 16, 3, 3)
            x += 20

        self.setFixedWidth(x + 2)
        p.end()


class ButtonEditorDialog(QDialog):
    """
    Edit a single InputSlot's label, size, position and colour.
    on_change(slot) is called immediately when Apply is clicked so the
    panel can repaint live. The caller handles Save/Revert.

    A class-level style cache (_style_cache) persists across dialog
    instances so Copy Style / Apply Style work between different buttons.
    """

    # Class-level cache: survives across dialog open/close
    _style_cache: dict = {}   # {"size": int, "color": str, "border": str}

    def __init__(
        self,
        slot: InputSlot,
        default_size: int,
        on_change: Callable[[InputSlot], None],
        resolved_color: str = "#e63946",
        resolved_border: str = "#ff6b6b",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._slot           = slot
        self._original       = deepcopy(slot)
        self._on_change      = on_change
        self._default_sz     = default_size
        self._resolved_color  = resolved_color
        self._resolved_border = resolved_border

        self.setWindowTitle(f"Edit — {slot.id}")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(_STYLE)
        self.setFixedWidth(320)

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel(f"Button: {slot.id.upper()}")
        title.setObjectName("title")
        root.addWidget(title)

        # Label
        lbl_row = QWidget()
        lbl_row.setStyleSheet("background: transparent;")
        lr = QHBoxLayout(lbl_row)
        lr.setContentsMargins(0, 0, 0, 0)
        lr.setSpacing(8)
        lr.addWidget(QLabel("Label"))
        self._label_edit = QLineEdit(slot.label.replace("\n", "\\n"))
        self._label_edit.setPlaceholderText('e.g. "Jump" or "Light\\nPunch"')
        lr.addWidget(self._label_edit, stretch=1)
        root.addWidget(lbl_row)

        hint = QLabel('Use \\n to split onto two lines. "Unused" = greyed out.')
        hint.setObjectName("hint")
        root.addWidget(hint)

        # Quick symbol picker — two rows of glyphs + Unused button
        _QUICK_SYMBOLS = [
            # PS shapes
            ("△", "PS Triangle"), ("□", "PS Square"),
            ("○", "PS Circle"),   ("✕", "PS Cross"),
            # Filled arrows (consistent weight)
            ("▲", "Up"),   ("▼", "Down"),
            ("◀", "Left"), ("▶", "Right"),
            # Common gaming symbols
            ("★", "Star"),   ("♦", "Diamond"),
            ("⊕", "Plus"),   ("⊗", "Cross circle"),
            ("♠", "Spade"),  ("♣", "Club"),
        ]

        _SYM_BTN_STYLE = (
            "QPushButton { background: #1a1a3a; color: #ffffff; border: 1px solid #333366;"
            "border-radius: 4px; font-size: 13px; padding: 0; }"
            "QPushButton:hover { background: #2a2a5a; border-color: #6644cc; }"
            "QPushButton:pressed { background: #6644cc; }"
        )

        # Split into two rows of 7
        row_size = 7
        for row_idx in range(0, len(_QUICK_SYMBOLS), row_size):
            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            sym_row = QHBoxLayout(row_widget)
            sym_row.setContentsMargins(0, 0, 0, 0)
            sym_row.setSpacing(3)
            for glyph, tooltip in _QUICK_SYMBOLS[row_idx:row_idx + row_size]:
                btn = QPushButton(glyph)
                btn.setFixedSize(26, 26)
                btn.setToolTip(tooltip)
                btn.setStyleSheet(_SYM_BTN_STYLE)
                btn.clicked.connect(lambda checked, g=glyph: self._insert_symbol(g))
                sym_row.addWidget(btn)
            sym_row.addStretch()
            root.addWidget(row_widget)

        # Unused button — sets label to Unused and closes
        unused_btn = QPushButton("⬜  Mark as Unused")
        unused_btn.setStyleSheet(
            "QPushButton { background: #2a2a2a; color: #888888; border: 1px solid #444444;"
            "border-radius: 5px; padding: 5px 10px; font-size: 11px; }"
            "QPushButton:hover { background: #333333; color: #aaaaaa; border-color: #666666; }"
            "QPushButton:pressed { background: #1a1a1a; }"
        )
        unused_btn.clicked.connect(self._mark_unused)
        root.addWidget(unused_btn)

        # Size
        self._size = _SpinRow("Size", slot.size if slot.size else default_size, 10, 200, step=2)
        root.addWidget(self._size)

        # Position
        self._x = _SpinRow("X", slot.x, -2000, 4000, step=1)
        self._y = _SpinRow("Y", slot.y, -2000, 4000, step=1)
        root.addWidget(self._x)
        root.addWidget(self._y)

        # Colours (only for action buttons, not directions)
        self._color_row  = None
        self._border_row = None
        if slot.kind == "button":
            # Use resolved (on-screen) color as initial value so dialog matches what's rendered
            self._color_row  = _ColorRow("Colour",  slot.color  or resolved_color)
            self._border_row = _ColorRow("Border",  slot.border or resolved_border)
            root.addWidget(self._color_row)
            root.addWidget(self._border_row)

        # Style clipboard row (only for buttons, not directions)
        if slot.kind == "button":
            style_row = QHBoxLayout()
            style_row.setSpacing(6)

            copy_style_btn = QPushButton("📋  Copy Style")
            copy_style_btn.setToolTip("Copy size and colours to clipboard")
            copy_style_btn.setStyleSheet(
                "QPushButton { background: #1a3a5a; color: #88ccff; border: 1px solid #2255aa;"
                "border-radius: 5px; padding: 5px 10px; font-size: 11px; }"
                "QPushButton:hover { background: #1e4a70; }"
                "QPushButton:pressed { background: #0a2a44; }"
            )
            copy_style_btn.clicked.connect(self._copy_style)
            style_row.addWidget(copy_style_btn)

            self._apply_style_btn = QPushButton("Apply Style")
            self._apply_style_btn.setToolTip("Apply copied size and colours")
            self._apply_style_btn.setEnabled(bool(ButtonEditorDialog._style_cache))
            self._apply_style_btn.setStyleSheet(
                "QPushButton { background: #1a3a2a; color: #88ffaa; border: 1px solid #225533;"
                "border-radius: 5px; padding: 5px 10px; font-size: 11px; }"
                "QPushButton:hover { background: #1e4a30; }"
                "QPushButton:pressed { background: #0a2a18; }"
                "QPushButton:disabled { background: #1a1a2a; color: #445544; border-color: #222233; }"
            )
            self._apply_style_btn.clicked.connect(self._apply_style)
            style_row.addWidget(self._apply_style_btn)
            style_row.addStretch()

            # Cache preview: size in px + two colour swatches
            self._cache_preview = _CachePreview()
            self._cache_preview.update_cache(ButtonEditorDialog._style_cache)
            style_row.addWidget(self._cache_preview)

            root.addLayout(style_row)

        # Buttons
        btn_row = QHBoxLayout()
        revert_btn = QPushButton("Revert")
        revert_btn.clicked.connect(self._revert)
        apply_btn  = QPushButton("Apply")
        apply_btn.setObjectName("applyBtn")
        apply_btn.setStyleSheet(
            "QPushButton#applyBtn {"
            "  background: #6644cc; color: #fff; border: 1px solid #9977ff;"
            "  border-radius: 6px; padding: 7px 16px; font-size: 12px; font-weight: bold;"
            "}"
            "QPushButton#applyBtn:hover  { background: #7755dd; }"
            "QPushButton#applyBtn:pressed { background: #4433aa; border-color: #6655cc; }"
        )
        apply_btn.clicked.connect(self._apply_with_feedback)
        close_btn  = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(revert_btn)
        btn_row.addStretch()
        btn_row.addWidget(apply_btn)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _mark_unused(self) -> None:
        """Set label to Unused, apply and close."""
        self._label_edit.setText("Unused")
        self._collect()
        self._on_change(self._slot)
        self.accept()

    def _insert_symbol(self, glyph: str) -> None:
        """Replace label with glyph, or append if label has text content."""
        current = self._label_edit.text().strip()
        # If current label is empty, a single symbol, or "Unused" — replace it
        if not current or len(current) <= 2 or current.lower() == "unused":
            self._label_edit.setText(glyph)
        else:
            # Append to existing label (useful for "L +" style combos)
            self._label_edit.setText(current + glyph)
        self._label_edit.setFocus()

    def _copy_style(self) -> None:
        """Copy current size and colours to the class-level cache."""
        ButtonEditorDialog._style_cache = {
            "size":   self._size.value(),
            "color":  self._color_row.value() if self._color_row else "",
            "border": self._border_row.value() if self._border_row else "",
        }
        self._update_cache_preview()
        if hasattr(self, "_apply_style_btn"):
            self._apply_style_btn.setEnabled(True)
        # Flash the copy button
        btn = self.sender()
        if btn:
            orig = btn.styleSheet()
            btn.setText("✓ Copied")
            from PyQt6.QtCore import QTimer
            def restore():
                try:
                    btn.setStyleSheet(orig)
                    btn.setText("📋  Copy Style")
                except RuntimeError:
                    pass
            QTimer.singleShot(500, restore)

    def _apply_style(self) -> None:
        """Apply cached size and colours to the current button."""
        cache = ButtonEditorDialog._style_cache
        if not cache:
            return
        if "size" in cache:
            self._size.set_value(cache["size"])
        if "color" in cache and self._color_row:
            self._color_row._color = cache["color"]
            self._color_row._update_swatch()
        if "border" in cache and self._border_row:
            self._border_row._color = cache["border"]
            self._border_row._update_swatch()

    def _update_cache_preview(self) -> None:
        if hasattr(self, "_cache_preview"):
            self._cache_preview.update_cache(ButtonEditorDialog._style_cache)

    def _collect(self) -> None:
        raw_label = self._label_edit.text()
        self._slot.label  = raw_label.replace("\\n", "\n")
        self._slot.x      = self._x.value()
        self._slot.y      = self._y.value()
        sz = self._size.value()
        self._slot.size   = 0 if sz == self._default_sz else sz
        if self._color_row:
            self._slot.color  = self._color_row.value()
        if self._border_row:
            self._slot.border = self._border_row.value()

    def _apply(self) -> None:
        self._collect()
        self._on_change(self._slot)

    def _apply_with_feedback(self) -> None:
        """Apply changes and flash the button green briefly."""
        self._collect()
        self._on_change(self._slot)
        # Find the apply button and flash it
        from PyQt6.QtCore import QTimer
        btn = self.sender()
        if btn:
            original_style = btn.styleSheet()
            btn.setStyleSheet(
                "QPushButton { background: #227722; color: #fff; border: 1px solid #44bb44;"
                "border-radius: 6px; padding: 7px 16px; font-size: 12px; font-weight: bold; }"
            )
            btn.setText("✓ Applied")
            def restore():
                try:
                    btn.setStyleSheet(original_style)
                    btn.setText("Apply")
                except RuntimeError:
                    pass  # dialog was closed before timer fired
            QTimer.singleShot(600, restore)

    def _revert(self) -> None:
        # Restore original values
        self._slot.label  = self._original.label
        self._slot.x      = self._original.x
        self._slot.y      = self._original.y
        self._slot.size   = self._original.size
        self._slot.color  = self._original.color
        self._slot.border = self._original.border
        # Refresh UI fields
        self._label_edit.setText(self._slot.label.replace("\n", "\\n"))
        self._x.set_value(self._slot.x)
        self._y.set_value(self._slot.y)
        self._size.set_value(self._slot.size if self._slot.size else self._default_sz)
        if self._color_row:
            self._color_row._color = self._slot.color or "#e63946"
            self._color_row._update_swatch()
        if self._border_row:
            self._border_row._color = self._slot.border or "#ff6b6b"
            self._border_row._update_swatch()
        self._on_change(self._slot)