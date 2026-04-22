"""
stickui.ui.background
~~~~~~~~~~~~~~~~~~~~~
Cover-scaled background widget with configurable darkening overlay.

The darkening is a flat black overlay with configurable opacity,
applied on top of the image before the vignette.

Config key: background_dim  (float 0.0–1.0, default 0.55)
  0.0 = no darkening (original image brightness)
  0.55 = moderate darkening (default, good for most LaunchBox fanart)
  1.0 = fully black

Priority: game.toml > system.toml > config.toml > built-in default
The resolved value is passed in via set_dim().
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget


class BackgroundWidget(QWidget):

    def __init__(
        self,
        parent=None,
        image_path: Optional[str] = None,
        panel_color: str = "#0d0d0d",
        dim: float = 0.55,
    ) -> None:
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None
        self._panel_color = panel_color
        self._dim = max(0.0, min(1.0, dim))
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

    def set_dim(self, dim: float) -> None:
        self._dim = max(0.0, min(1.0, dim))
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
        super().paintEvent(event)

    def _paint_cover(self, p: QPainter, w: int, h: int) -> None:
        img_w = self._pixmap.width()
        img_h = self._pixmap.height()

        scale    = max(w / img_w, h / img_h)
        scaled_w = int(img_w * scale)
        scaled_h = int(img_h * scale)
        ox = (w - scaled_w) // 2
        oy = (h - scaled_h) // 2

        p.drawPixmap(QRect(ox, oy, scaled_w, scaled_h), self._pixmap)

        # Flat darkening overlay
        if self._dim > 0.0:
            alpha = int(self._dim * 255)
            p.fillRect(0, 0, w, h, QColor(0, 0, 0, alpha))

        # Vignette on top of the darkening
        vignette = QLinearGradient(0, 0, 0, h)
        vignette.setColorAt(0,   QColor(0, 0, 0, 80))
        vignette.setColorAt(0.4, QColor(0, 0, 0, 0))
        vignette.setColorAt(1,   QColor(0, 0, 0, 80))
        p.fillRect(0, 0, w, h, vignette)

    def _paint_gradient(self, p: QPainter, w: int, h: int) -> None:
        c = QColor(self._panel_color)
        lighter = c.lighter(140)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, lighter)
        grad.setColorAt(1, c)
        p.fillRect(0, 0, w, h, grad)