"""
controlpad.ui.panel
~~~~~~~~~~~~~~~~~~~
The ControlPanel widget renders the visual joystick / button layout.

It uses QPainter to draw directly — no third-party widget lib needed —
which gives pixel-perfect control over shapes, colours, and shadows.

Layout styles
-------------
arcade   – joystick on the left, button grid on the right
gamepad  – two sticks + d-pad + face buttons (SNES style)
keyboard – a simple grid of labelled rectangles
custom   – uses [layout] positions from the game toml verbatim
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QPoint, QRect, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter,
    QPainterPath, QPen, QRadialGradient,
)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..core.layout import ButtonInfo, LayoutResult


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BTN_MIN   = 38   # minimum button diameter (px)
BTN_MAX   = 72   # maximum button diameter (px)
BTN_GAP   = 10   # gap between buttons
STICK_R   = 36   # joystick base radius
DPAD_W    = 26   # d-pad arm width


# ---------------------------------------------------------------------------
# Helper: darken / lighten a hex colour
# ---------------------------------------------------------------------------

def _adjust(hex_color: str, factor: float) -> str:
    c = QColor(hex_color)
    h, s, v, a = c.getHsvF()
    v = max(0.0, min(1.0, v * factor))
    c.setHsvF(h, s, v, a)
    return c.name()


# ---------------------------------------------------------------------------
# ControlPanel
# ---------------------------------------------------------------------------

class ControlPanel(QWidget):
    """
    Draws the full control layout using QPainter.
    """

    def __init__(self, layout_result: LayoutResult, parent=None) -> None:
        super().__init__(parent)
        self.lr = layout_result
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: transparent;")

    # ── Paint dispatch ──────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        style = self.lr.style

        if style == "arcade":
            self._paint_arcade(painter)
        elif style == "gamepad":
            self._paint_gamepad(painter)
        else:
            self._paint_grid(painter)

        painter.end()

    # ── Arcade layout ───────────────────────────────────────────────────────

    def _paint_arcade(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        margin = 20

        # Left side: joystick
        stick_cx = margin + STICK_R + 10
        stick_cy = h // 2

        self._draw_stick(painter, stick_cx, stick_cy)

        # Right side: button grid
        # Detect how many cols / rows the buttons need
        buttons = [b for b in self.lr.buttons if not b.is_axis]
        if not buttons:
            return

        cols = max(b.col for b in buttons) + 1
        rows = max(b.row for b in buttons) + 1

        # Size buttons to fill the right portion of the widget
        avail_w = w - (stick_cx + STICK_R + margin * 2) - margin
        avail_h = h - margin * 2

        btn_d = min(
            BTN_MAX,
            max(BTN_MIN, (avail_w - BTN_GAP * (cols - 1)) // cols),
            (avail_h - BTN_GAP * (rows - 1)) // rows,
        )

        grid_w = cols * btn_d + (cols - 1) * BTN_GAP
        grid_h = rows * btn_d + (rows - 1) * BTN_GAP

        origin_x = w - margin - grid_w
        origin_y = (h - grid_h) // 2

        for btn in buttons:
            cx = origin_x + btn.col * (btn_d + BTN_GAP) + btn_d // 2
            cy = origin_y + btn.row * (btn_d + BTN_GAP) + btn_d // 2
            self._draw_button(painter, cx, cy, btn_d, btn)

        # Action / start buttons at the bottom centre
        meta = [b for b in self.lr.buttons if b.is_axis is False
                and b.id in ("START1", "COIN1", "START", "SELECT")]
        if meta:
            meta_y = h - margin - BTN_MIN // 2
            total_meta_w = len(meta) * (BTN_MIN + BTN_GAP) - BTN_GAP
            meta_x_start = w // 2 - total_meta_w // 2
            for i, btn in enumerate(meta):
                cx = meta_x_start + i * (BTN_MIN + BTN_GAP) + BTN_MIN // 2
                self._draw_button(painter, cx, meta_y, BTN_MIN, btn, shape="rounded")

    # ── Gamepad layout ──────────────────────────────────────────────────────

    def _paint_gamepad(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        margin = 24
        mid_y = h // 2

        # Left stick / d-pad
        self._draw_dpad(painter, margin + STICK_R, mid_y)

        # Right face buttons (ABXY / BAYX)
        face = [b for b in self.lr.buttons
                if b.id in ("A", "B", "X", "Y", "BUTTON1", "BUTTON2",
                             "BUTTON3", "BUTTON4")]
        if face:
            btn_d = min(BTN_MAX, (w // 2 - margin) // 3)
            face_cx = w - margin - btn_d * 1.5
            face_cy = mid_y

            # Fixed cross pattern
            offsets = {"A": (1, 0), "B": (0, 1), "X": (0, -1), "Y": (-1, 0),
                       "BUTTON1": (0, 1), "BUTTON2": (1, 0),
                       "BUTTON3": (-1, 0), "BUTTON4": (0, -1)}
            step = btn_d + BTN_GAP
            for btn in face:
                dx, dy = offsets.get(btn.id, (0, 0))
                cx = int(face_cx + dx * step)
                cy = int(face_cy + dy * step)
                self._draw_button(painter, cx, cy, btn_d, btn)

        # Shoulder buttons
        shoulders = [b for b in self.lr.buttons if b.id in ("L", "R", "L2", "R2")]
        if shoulders:
            sb_w, sb_h = 60, 22
            left_sb  = [b for b in shoulders if b.id.startswith("L")]
            right_sb = [b for b in shoulders if b.id.startswith("R")]

            for i, btn in enumerate(left_sb):
                rx = margin
                ry = margin + i * (sb_h + 6)
                self._draw_shoulder(painter, rx, ry, sb_w, sb_h, btn)

            for i, btn in enumerate(right_sb):
                rx = w - margin - sb_w
                ry = margin + i * (sb_h + 6)
                self._draw_shoulder(painter, rx, ry, sb_w, sb_h, btn)

        # Start / Select
        meta = [b for b in self.lr.buttons if b.id in ("START", "SELECT", "START1", "COIN1")]
        if meta:
            total = len(meta)
            meta_total_w = total * (BTN_MIN + BTN_GAP) - BTN_GAP
            x0 = (w - meta_total_w) // 2
            for i, btn in enumerate(meta):
                cx = x0 + i * (BTN_MIN + BTN_GAP) + BTN_MIN // 2
                self._draw_button(painter, cx, h - margin - BTN_MIN // 2,
                                  BTN_MIN, btn, shape="rounded")

    # ── Generic grid ───────────────────────────────────────────────────────

    def _paint_grid(self, painter: QPainter) -> None:
        buttons = self.lr.buttons
        if not buttons:
            return

        w, h = self.width(), self.height()
        margin = 20
        cols = max(b.col for b in buttons) + 1
        rows = max(b.row for b in buttons) + 1

        btn_d = min(
            BTN_MAX,
            max(BTN_MIN, (w - 2 * margin - BTN_GAP * (cols - 1)) // cols),
        )
        grid_w = cols * btn_d + (cols - 1) * BTN_GAP
        grid_h = rows * btn_d + (rows - 1) * BTN_GAP
        ox = (w - grid_w) // 2
        oy = (h - grid_h) // 2

        for btn in buttons:
            cx = ox + btn.col * (btn_d + BTN_GAP) + btn_d // 2
            cy = oy + btn.row * (btn_d + BTN_GAP) + btn_d // 2
            self._draw_button(painter, cx, cy, btn_d, btn)

    # ── Drawing primitives ──────────────────────────────────────────────────

    def _draw_button(
        self,
        p: QPainter,
        cx: int,
        cy: int,
        diameter: int,
        btn: ButtonInfo,
        shape: str = "circle",
    ) -> None:
        color = btn.color or self.lr.button_color
        border = self.lr.button_border_color
        label_color = self.lr.button_label_color
        r = diameter // 2

        # Shadow
        shadow_grad = QRadialGradient(cx + 2, cy + 4, r + 6)
        shadow_grad.setColorAt(0, QColor(0, 0, 0, 80))
        shadow_grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(shadow_grad))
        p.drawEllipse(cx - r - 4, cy - r - 2, (r + 4) * 2, (r + 4) * 2)

        # Radial gradient fill
        grad = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.4)
        grad.setColorAt(0, QColor(_adjust(color, 1.4)))
        grad.setColorAt(0.6, QColor(color))
        grad.setColorAt(1, QColor(_adjust(color, 0.7)))

        p.setPen(QPen(QColor(border), 2))
        p.setBrush(QBrush(grad))

        if shape == "rounded":
            rect = QRectF(cx - r, cy - r // 2, diameter, r)
            p.drawRoundedRect(rect, 8, 8)
        else:
            p.drawEllipse(QPoint(cx, cy), r, r)

        # Specular highlight
        hi = QRadialGradient(cx - r * 0.25, cy - r * 0.35, r * 0.5)
        hi.setColorAt(0, QColor(255, 255, 255, 60))
        hi.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(hi))
        p.drawEllipse(QPoint(cx, cy), r, r)

        # Label
        p.setPen(QColor(label_color))
        font = QFont("sans-serif", max(7, diameter // 6), QFont.Weight.Bold)
        p.setFont(font)
        text_rect = QRect(cx - r, cy - r, diameter, diameter)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, btn.label)

    def _draw_stick(self, p: QPainter, cx: int, cy: int) -> None:
        color = self.lr.stick_color
        border = _adjust(color, 1.5)

        # Base plate
        base_r = STICK_R + 10
        grad = QRadialGradient(cx, cy, base_r)
        grad.setColorAt(0, QColor(_adjust(color, 1.2)))
        grad.setColorAt(1, QColor(_adjust(color, 0.6)))
        p.setPen(QPen(QColor(border), 2))
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPoint(cx, cy), base_r, base_r)

        # Ball
        ball_r = STICK_R // 2
        p.setPen(QPen(QColor(border), 1))
        p.setBrush(QBrush(QColor(_adjust(color, 1.6))))
        p.drawEllipse(QPoint(cx, cy - STICK_R // 3), ball_r, ball_r)

    def _draw_dpad(self, p: QPainter, cx: int, cy: int) -> None:
        arm = DPAD_W
        length = STICK_R

        color = self.lr.stick_color
        border = _adjust(color, 1.5)

        p.setPen(QPen(QColor(border), 1.5))
        p.setBrush(QBrush(QColor(color)))

        # Horizontal arm
        p.drawRoundedRect(cx - length, cy - arm // 2, length * 2, arm, 4, 4)
        # Vertical arm
        p.drawRoundedRect(cx - arm // 2, cy - length, arm, length * 2, 4, 4)

        # Centre circle
        p.setBrush(QBrush(QColor(_adjust(color, 1.3))))
        p.drawEllipse(QPoint(cx, cy), arm // 2, arm // 2)

    def _draw_shoulder(
        self, p: QPainter, x: int, y: int, w: int, h: int, btn: ButtonInfo
    ) -> None:
        color = btn.color or self.lr.button_color
        border = self.lr.button_border_color
        label_color = self.lr.button_label_color

        p.setPen(QPen(QColor(border), 1.5))
        p.setBrush(QBrush(QColor(color)))
        p.drawRoundedRect(x, y, w, h, 6, 6)

        p.setPen(QColor(label_color))
        font = QFont("sans-serif", 8, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter, btn.label)