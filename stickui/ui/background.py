"""
stickui.ui.background
~~~~~~~~~~~~~~~~~~~~~
A QWidget subclass that paints a background image scaled to cover
the full widget area (like CSS background-size: cover).

The image is scaled so the shorter dimension fills the widget,
then centred — no empty borders, no distortion.
Falls back to a gradient if no image is provided.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QRect, QRectF
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget


class BackgroundWidget(QWidget):
    """
    Drop-in replacement for a plain QWidget that paints a cover-scaled
    background image (or gradient fallback) before child widgets are drawn.
    """

    def __init__(
        self,
        parent=None,
        image_path: Optional[str] = None,
        panel_color: str = "#0d0d0d",
    ) -> None:
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None
        self._panel_color = panel_color
        self.set_image(image_path)

    def set_image(self, image_path: Optional[str]) -> None:
        if image_path:
            px = QPixmap(image_path)
            self._pixmap = px if not px.isNull() else None
        else:
            self._pixmap = None
        self.update()

    def set_panel_color(self, color: str) -> None:
        self._panel_color = color
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()

        if self._pixmap and not self._pixmap.isNull():
            self._paint_cover(p, w, h)
        else:
            self._paint_gradient(p, w, h)

        p.end()
        # Let child widgets paint on top
        super().paintEvent(event)

    def _paint_cover(self, p: QPainter, w: int, h: int) -> None:
        """Scale image to cover the widget (like CSS cover), then centre."""
        img_w = self._pixmap.width()
        img_h = self._pixmap.height()

        # Scale factor: the larger ratio wins so both sides are covered
        scale = max(w / img_w, h / img_h)

        scaled_w = int(img_w * scale)
        scaled_h = int(img_h * scale)

        # Centre the scaled image
        ox = (w - scaled_w) // 2
        oy = (h - scaled_h) // 2

        target = QRect(ox, oy, scaled_w, scaled_h)
        p.drawPixmap(target, self._pixmap)

        # Subtle dark vignette so UI elements remain readable
        vignette = QLinearGradient(0, 0, 0, h)
        vignette.setColorAt(0, QColor(0, 0, 0, 120))
        vignette.setColorAt(0.4, QColor(0, 0, 0, 40))
        vignette.setColorAt(1, QColor(0, 0, 0, 140))
        p.fillRect(0, 0, w, h, vignette)

    def _paint_gradient(self, p: QPainter, w: int, h: int) -> None:
        """Fallback: diagonal gradient based on panel_color."""
        c = QColor(self._panel_color)
        lighter = c.lighter(140)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, lighter)
        grad.setColorAt(1, c)
        p.fillRect(0, 0, w, h, grad)