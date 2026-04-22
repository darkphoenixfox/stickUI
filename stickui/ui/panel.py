"""
stickui.ui.panel
~~~~~~~~~~~~~~~~
Renders the stick layout using absolute pixel positions from the stick config.
Labels auto-fit inside buttons; long labels spill below with an abbreviation inside.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPen, QRadialGradient,
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
    """Normalise labels: convert literal \n sequences to real newlines."""
    return label.replace("\\n", "\n")


class ControlPanel(QWidget):

    def __init__(
        self,
        layout_result: LayoutResult,
        stick_layout: StickLayout | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.lr = layout_result
        self.sl = stick_layout
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.sl:
            self._paint_from_stick(p)
        else:
            self._paint_fallback(p)
        p.end()

    # ── Stick-based rendering ───────────────────────────────────────────────

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

    # ── Fallback grid ───────────────────────────────────────────────────────

    def _paint_fallback(self, p: QPainter) -> None:
        w, h = self.width(), self.height()
        margin = 20
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
            slot = InputSlot(id=btn.id, x=cx, y=cy,
                             label=btn.label, kind="button")
            self._draw_button(p, slot, btn_d,
                              self.lr.button_color,
                              self.lr.button_border_color,
                              self.lr.button_label_color)

    # ── Button ──────────────────────────────────────────────────────────────

    def _draw_button(
        self,
        p: QPainter,
        slot: InputSlot,
        diameter: int,
        color: str,
        border: str,
        label_color: str,
    ) -> None:
        cx, cy = slot.x, slot.y
        r = diameter // 2

        # Shadow
        shadow = QRadialGradient(cx + 2, cy + 4, r + 6)
        shadow.setColorAt(0, QColor(0, 0, 0, 80))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(shadow))
        p.drawEllipse(cx - r - 4, cy - r - 2, (r + 4) * 2, (r + 4) * 2)

        # Fill
        grad = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.4)
        grad.setColorAt(0, QColor(_adjust(color, 1.4)))
        grad.setColorAt(0.6, QColor(color))
        grad.setColorAt(1, QColor(_adjust(color, 0.7)))
        p.setPen(QPen(QColor(border), 2))
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPoint(cx, cy), r, r)

        # Specular highlight
        hi = QRadialGradient(cx - r * 0.25, cy - r * 0.35, r * 0.5)
        hi.setColorAt(0, QColor(255, 255, 255, 60))
        hi.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(hi))
        p.drawEllipse(QPoint(cx, cy), r, r)

        label = _norm(slot.label)

        # "Unused" = explicitly marked as unused — render greyed out
        if label.strip().lower() == "unused":
            self._draw_button_unused(p, cx, cy, r)
            return

        inner = int(r * 1.35)   # usable px width inside circle

        # Build candidate line-break versions to try:
        # 1. Label as-is (may already have explicit newlines)
        # 2. Word-wrapped into 2 lines at the natural midpoint
        def wrap_two_lines(text: str) -> str:
            words = text.split()
            if len(words) <= 1:
                return text
            mid = len(words) // 2
            return "\n".join([" ".join(words[:mid]), " ".join(words[mid:])])

        base_lines = label.split("\n")
        candidates = [base_lines]
        if len(base_lines) == 1 and " " in label:
            candidates.append(wrap_two_lines(label).split("\n"))

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
            if fitted_fs is not None:
                break

        if fitted_fs is not None:
            p.setPen(QColor(label_color))
            p.setFont(QFont("sans-serif", fitted_fs, QFont.Weight.Bold))
            p.drawText(btn_rect,
                       Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       "\n".join(fitted_lines))
        else:
            # Still too long — initials inside, full label below
            words = label.replace("\n", " ").split()
            abbrev = "".join(w[0].upper() for w in words if w)
            p.setPen(QColor(label_color))
            p.setFont(QFont("sans-serif", max(7, diameter // 4), QFont.Weight.Bold))
            p.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, abbrev)

            below_fs = max(6, diameter // 7)
            p.setFont(QFont("sans-serif", below_fs))
            p.setPen(QColor(255, 255, 255, 210))
            below_rect = QRect(cx - r - 14, cy + r + 3, diameter + 28, 32)
            p.drawText(below_rect,
                       Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       label)

    # ── Unused button ──────────────────────────────────────────────────────

    def _draw_button_unused(self, p: QPainter, cx: int, cy: int, r: int) -> None:
        """Greyed-out button with 'Unused' label."""
        color  = "#2a2a2a"
        border = "#3a3a3a"

        # Shadow (subtle)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 40)))
        p.drawEllipse(cx - r - 2, cy - r, (r + 2) * 2, (r + 2) * 2)

        # Fill — flat dark circle
        p.setPen(QPen(QColor(border), 1))
        p.setBrush(QBrush(QColor(color)))
        p.drawEllipse(QPoint(cx, cy), r, r)

        # "Unused" label
        fs = max(6, r // 4)
        p.setFont(QFont("sans-serif", fs))
        p.setPen(QColor(80, 80, 80))
        p.drawText(
            QRect(cx - r, cy - r, r * 2, r * 2),
            Qt.AlignmentFlag.AlignCenter,
            "Unused",
        )

    # ── Arrow ───────────────────────────────────────────────────────────────

    def _draw_arrow(
        self,
        p: QPainter,
        slot: InputSlot,
        size: int,
        color: str,
        label_color: str,
    ) -> None:
        cx, cy = slot.x, slot.y
        r = size // 2
        x, y = cx - r, cy - r
        border = _adjust(color, 1.8)

        # Shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 55)))
        p.drawRoundedRect(x + 2, y + 3, size, size, 7, 7)

        # Fill
        from PyQt6.QtGui import QRadialGradient
        grad = QRadialGradient(cx - r * 0.2, cy - r * 0.2, r * 1.5)
        grad.setColorAt(0, QColor(_adjust(color, 1.5)))
        grad.setColorAt(1, QColor(_adjust(color, 0.7)))
        p.setPen(QPen(QColor(border), 1.5))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(x, y, size, size, 7, 7)

        # Arrow glyph
        glyph = _ARROW_GLYPH.get(slot.id, "\u2022")
        p.setPen(QColor(label_color))
        p.setFont(QFont("sans-serif", max(10, size // 3), QFont.Weight.Bold))
        p.drawText(QRect(x, y, size, size), Qt.AlignmentFlag.AlignCenter, glyph)

        # Custom label below (only if different from default)
        default = _DIR_DEFAULTS.get(slot.id, "")
        display_label = _norm(slot.label)
        if display_label and display_label != default:
            p.setFont(QFont("sans-serif", 7))
            p.setPen(QColor(255, 255, 255, 160))
            p.drawText(
                QRect(x - 12, y + size + 2, size + 24, 14),
                Qt.AlignmentFlag.AlignCenter,
                display_label,
            )