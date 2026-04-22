"""
stickui.ui.panel
~~~~~~~~~~~~~~~~
Renders the stick layout. Supports an edit mode where clicking a button
opens a ButtonEditorDialog to change label, size, position and colour.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient,
)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..core.layout import LayoutResult
from ..core.stick import InputSlot, StickLayout


_ARROW_GLYPH = {
    "up":    "\u25b2",
    "down":  "\u25bc",
    "left":  "\u25c0",
    "right": "\u25b6",
}

_DIR_DEFAULTS = {"up": "Up", "down": "Down", "left": "Left", "right": "Right"}


def _adjust(hex_color: str, factor: float) -> str:
    c = QColor(hex_color)
    h, s, v, a = c.getHsvF()
    v = max(0.0, min(1.0, v * factor))
    c.setHsvF(h, s, v, a)
    return c.name()


def _norm(label: str) -> str:
    return label.replace("\\n", "\n")


# PS button symbols that need consistent drawn weight
_PS_SYMBOLS = {
    "△": "triangle",
    "▲": "triangle",
    "□": "square",
    "■": "square",
    "○": "circle",
    "◯": "circle",
    "✕": "cross",    # U+2715 Multiplication X
    "×": "cross",    # U+00D7 Multiplication sign
    "✖": "cross",    # U+2716 Heavy Multiplication X
    # Note: plain "X" intentionally excluded — it's a letter, not a PS symbol
}


def _draw_ps_symbol(p: QPainter, symbol: str, cx: int, cy: int, r: int, color: str) -> bool:
    """
    Draw a PS button symbol with consistent stroke weight.
    Returns True if symbol was drawn, False if not a PS symbol.
    """
    key = _PS_SYMBOLS.get(symbol.strip())
    if not key:
        return False

    pen_w = max(2, r // 6)
    p.setPen(QPen(QColor(color), pen_w, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    sr = int(r * 0.45)   # symbol radius — fraction of button radius

    if key == "circle":
        p.drawEllipse(QPoint(cx, cy), sr, sr)

    elif key == "cross":
        d = int(sr * 0.75)
        p.drawLine(cx - d, cy - d, cx + d, cy + d)
        p.drawLine(cx + d, cy - d, cx - d, cy + d)

    elif key == "square":
        p.drawRect(QRect(cx - sr, cy - sr, sr * 2, sr * 2))

    elif key == "triangle":
        h = int(sr * 1.1)
        tip_y = cy - h
        base_y = cy + int(h * 0.5)
        bx = int(sr * 0.95)
        path = QPainterPath()
        path.moveTo(cx, tip_y)
        path.lineTo(cx + bx, base_y)
        path.lineTo(cx - bx, base_y)
        path.closeSubpath()
        p.drawPath(path)

    return True


class ControlPanel(QWidget):

    def __init__(
        self,
        layout_result: LayoutResult,
        stick_layout: Optional[StickLayout] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.lr = layout_result
        self.sl = stick_layout
        self._edit_mode = False
        self._on_slot_changed: Optional[Callable] = None  # callback after edit
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: transparent;")

    # ── Edit mode ───────────────────────────────────────────────────────────

    def set_edit_mode(self, enabled: bool, on_slot_changed: Optional[Callable] = None):
        self._edit_mode = enabled
        self._on_slot_changed = on_slot_changed
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        if not self._edit_mode or not self.sl:
            return
        pos = event.position().toPoint()
        slot = self._hit_test(pos)
        if slot:
            self._open_editor(slot)

    def _hit_test(self, pos: QPoint) -> Optional[InputSlot]:
        """Return the slot under the cursor, or None."""
        if not self.sl:
            return None
        for slot in self.sl.buttons + self.sl.directions:
            size = slot.size if slot.size else (
                self.sl.button_size if slot.kind == "button" else self.sl.arrow_size
            )
            r = size // 2
            dx = pos.x() - slot.x
            dy = pos.y() - slot.y
            if dx * dx + dy * dy <= r * r:
                return slot
        return None

    def _open_editor(self, slot: InputSlot):
        from .button_editor import ButtonEditorDialog
        default_sz = self.sl.button_size if slot.kind == "button" else self.sl.arrow_size

        # Resolve actual rendered color so the editor shows what's on screen
        resolved_color  = slot.color  if slot.color  else self.lr.button_color
        resolved_border = slot.border if slot.border else self.lr.button_border_color

        def on_change(s: InputSlot):
            self.update()
            if self._on_slot_changed:
                self._on_slot_changed()

        dlg = ButtonEditorDialog(slot, default_sz, on_change,
                                 resolved_color=resolved_color,
                                 resolved_border=resolved_border,
                                 parent=self)
        dlg.exec()

    # ── Paint ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.sl:
            self._paint_from_stick(p)
        else:
            self._paint_fallback(p)

        # Edit mode overlay — highlight hovered area and draw edit indicator
        if self._edit_mode:
            self._paint_edit_overlay(p)

        p.end()

    def _paint_edit_overlay(self, p: QPainter):
        """Draw a subtle pulsing edit-mode indicator on each button."""
        if not self.sl:
            return
        for slot in self.sl.buttons + self.sl.directions:
            size = slot.size if slot.size else (
                self.sl.button_size if slot.kind == "button" else self.sl.arrow_size
            )
            r = size // 2
            # Dashed highlight ring
            pen = QPen(QColor(255, 220, 50, 180), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPoint(slot.x, slot.y), r + 3, r + 3)

    # ── Stick rendering ─────────────────────────────────────────────────────

    def _paint_from_stick(self, p: QPainter) -> None:
        sl = self.sl
        lr = self.lr
        for slot in sl.directions:
            size = slot.size if slot.size else sl.arrow_size
            self._draw_arrow(p, slot, size, lr.stick_color, lr.button_label_color)
        for slot in sl.buttons:
            size   = slot.size   if slot.size   else sl.button_size
            color  = slot.color  if slot.color  else lr.button_color
            border = slot.border if slot.border else lr.button_border_color
            self._draw_button(p, slot, size, color, border, lr.button_label_color)

    def _paint_fallback(self, p: QPainter) -> None:
        w, h = self.width(), self.height()
        btn_d, gap = 52, 10
        buttons = [b for b in self.lr.buttons if not b.is_axis]
        if not buttons:
            return
        cols = max(b.col for b in buttons) + 1
        rows = max(b.row for b in buttons) + 1
        grid_w = cols * btn_d + (cols - 1) * gap
        grid_h = rows * btn_d + (rows - 1) * gap
        ox = (w - grid_w) // 2
        oy = (h - grid_h) // 2
        for btn in buttons:
            cx = ox + btn.col * (btn_d + gap) + btn_d // 2
            cy = oy + btn.row * (btn_d + gap) + btn_d // 2
            slot = InputSlot(id=btn.id, x=cx, y=cy, label=btn.label, kind="button")
            self._draw_button(p, slot, btn_d, self.lr.button_color,
                              self.lr.button_border_color, self.lr.button_label_color)

    # ── Button ──────────────────────────────────────────────────────────────

    def _draw_button(self, p, slot, diameter, color, border, label_color):
        cx, cy = slot.x, slot.y
        r = diameter // 2

        # Check for unused FIRST — before any shadow or fill is drawn
        label = _norm(slot.label)
        if label.strip().lower() == "unused":
            self._draw_button_unused(p, cx, cy, r)
            return
        if not label and not slot.label:
            return

        shadow = QRadialGradient(cx + 2, cy + 4, r + 6)
        shadow.setColorAt(0, QColor(0, 0, 0, 80))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(shadow))
        p.drawEllipse(cx - r - 4, cy - r - 2, (r + 4) * 2, (r + 4) * 2)

        grad = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.4)
        grad.setColorAt(0, QColor(_adjust(color, 1.4)))
        grad.setColorAt(0.6, QColor(color))
        grad.setColorAt(1, QColor(_adjust(color, 0.7)))
        p.setPen(QPen(QColor(border), 2))
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPoint(cx, cy), r, r)

        hi = QRadialGradient(cx - r * 0.25, cy - r * 0.35, r * 0.5)
        hi.setColorAt(0, QColor(255, 255, 255, 60))
        hi.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(hi))
        p.drawEllipse(QPoint(cx, cy), r, r)

        if not label:
            return

        inner = int(r * 1.35)
        lines = label.split("\n")

        def wrap_two(text):
            words = text.split()
            if len(words) <= 1:
                return text
            mid = len(words) // 2
            return "\n".join([" ".join(words[:mid]), " ".join(words[mid:])])

        base_lines = lines
        candidates = [base_lines]
        if len(base_lines) == 1 and " " in label:
            candidates.append(wrap_two(label).split("\n"))

        btn_rect = QRect(cx - r, cy - r, diameter, diameter)
        fitted_fs = None
        fitted_lines = None

        for line_set in candidates:
            for fs in range(max(7, diameter // 4), 5, -1):
                f = QFont("sans-serif", fs, QFont.Weight.Bold)
                p.setFont(f)
                fm = p.fontMetrics()
                max_w = max(fm.horizontalAdvance(ln) for ln in line_set)
                total_h = fm.height() * len(line_set)
                if max_w <= inner and total_h <= inner:
                    fitted_fs = fs
                    fitted_lines = line_set
                    break
            if fitted_fs:
                break

        # Try drawing as a PS symbol first (consistent weight)
        if not _draw_ps_symbol(p, label.strip(), cx, cy, r, label_color):
            if fitted_fs:
                p.setPen(QColor(label_color))
                p.setFont(QFont("sans-serif", fitted_fs, QFont.Weight.Bold))
                p.drawText(btn_rect,
                           Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                           "\n".join(fitted_lines))
            else:
                words = label.replace("\n", " ").split()
                abbrev = "".join(w[0].upper() for w in words if w)
                p.setPen(QColor(label_color))
                p.setFont(QFont("sans-serif", max(7, diameter // 4), QFont.Weight.Bold))
                p.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, abbrev)
                p.setFont(QFont("sans-serif", max(6, diameter // 7)))
                p.setPen(QColor(255, 255, 255, 210))
                below = QRect(cx - r - 14, cy + r + 3, diameter + 28, 32)
                p.drawText(below, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, label)

    def _draw_button_unused(self, p, cx, cy, r):
        color  = getattr(self.lr, "unused_color",  "#2a2a2a")
        border = getattr(self.lr, "unused_border", "#4a4a4a")
        label  = getattr(self.lr, "unused_label",  "#505050")
        # Subtle shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 30)))
        p.drawEllipse(cx - r - 1, cy - r + 1, (r + 1) * 2, (r + 1) * 2)
        # Fill
        p.setPen(QPen(QColor(border), 1))
        p.setBrush(QBrush(QColor(color)))
        p.drawEllipse(QPoint(cx, cy), r, r)
        # Label
        p.setFont(QFont("sans-serif", max(6, r // 4)))
        p.setPen(QColor(label))
        p.drawText(QRect(cx - r, cy - r, r * 2, r * 2),
                   Qt.AlignmentFlag.AlignCenter, "Unused")

    # ── Arrow ───────────────────────────────────────────────────────────────

    def _draw_arrow(self, p, slot, size, color, label_color):
        cx, cy = slot.x, slot.y
        r = size // 2
        x, y = cx - r, cy - r
        border = _adjust(color, 1.8)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 55)))
        p.drawRoundedRect(x + 2, y + 3, size, size, 7, 7)

        grad = QRadialGradient(cx - r * 0.2, cy - r * 0.2, r * 1.5)
        grad.setColorAt(0, QColor(_adjust(color, 1.5)))
        grad.setColorAt(1, QColor(_adjust(color, 0.7)))
        p.setPen(QPen(QColor(border), 1.5))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(x, y, size, size, 7, 7)

        glyph = _ARROW_GLYPH.get(slot.id, "\u2022")
        p.setPen(QColor(label_color))
        p.setFont(QFont("sans-serif", max(10, size // 3), QFont.Weight.Bold))
        p.drawText(QRect(x, y, size, size), Qt.AlignmentFlag.AlignCenter, glyph)

        default = _DIR_DEFAULTS.get(slot.id, "")
        display_label = _norm(slot.label)
        if display_label and display_label != default:
            p.setFont(QFont("sans-serif", 7))
            p.setPen(QColor(255, 255, 255, 160))
            p.drawText(QRect(x - 12, y + size + 2, size + 24, 14),
                       Qt.AlignmentFlag.AlignCenter, display_label)