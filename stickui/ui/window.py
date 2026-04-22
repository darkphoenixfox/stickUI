"""
stickui.ui.window
~~~~~~~~~~~~~~~~~
Borderless, always-on-top overlay window.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QColor, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow,
    QMenu, QVBoxLayout, QWidget,
)

from ..core.layout import LayoutResult
from ..core.stick import StickLayout
from .panel import ControlPanel


class OverlayWindow(QMainWindow):

    def __init__(
        self,
        layout_result: LayoutResult,
        stick_layout: Optional[StickLayout] = None,
        x: int = 100,
        y: int = 100,
        width: int = 800,
        height: int = 300,
        opacity: float = 0.92,
        auto_hide_seconds: int = 0,
    ) -> None:
        super().__init__()
        self._drag_pos: Optional[QPoint] = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(opacity)
        self.setGeometry(x, y, width, height)
        self.setMinimumSize(300, 150)

        self._central = QWidget(self)
        self._central.setObjectName("centralWidget")
        self.setCentralWidget(self._central)
        self._apply_background(layout_result)

        root = QVBoxLayout(self._central)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)
        root.addWidget(self._build_header(layout_result))

        panel = ControlPanel(layout_result, stick_layout)
        root.addWidget(panel, stretch=1)

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, QApplication.quit)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        if auto_hide_seconds > 0:
            QTimer.singleShot(auto_hide_seconds * 1000, QApplication.quit)

    def _apply_background(self, lr: LayoutResult) -> None:
        if lr.background_path and lr.background_path.is_file():
            bg = str(lr.background_path).replace("\\", "/")
            self._central.setStyleSheet(
                f'#centralWidget {{'
                f'background-image: url("{bg}"); background-repeat: no-repeat;'
                f'background-position: center; border-radius: 14px;}}'
            )
        else:
            c = QColor(lr.panel_color)
            lighter = c.lighter(140).name()
            self._central.setStyleSheet(
                f'#centralWidget {{background: qlineargradient('
                f'x1:0,y1:0,x2:1,y2:1,stop:0 {lighter},stop:1 {lr.panel_color});'
                f'border-radius: 14px; border: 1px solid rgba(255,255,255,0.08);}}'
            )

    def _build_header(self, lr: LayoutResult) -> QWidget:
        container = QWidget()
        container.setFixedHeight(36)
        container.setStyleSheet("background: transparent;")
        hbox = QHBoxLayout(container)
        hbox.setContentsMargins(4, 0, 4, 0)

        title = lr.game_name or lr.system_name
        subtitle = lr.system_name if lr.game_name else ""

        title_col = QWidget()
        title_col.setStyleSheet("background: transparent;")
        from PyQt6.QtWidgets import QVBoxLayout as VBox
        tv = VBox(title_col)
        tv.setContentsMargins(0, 0, 0, 0)
        tv.setSpacing(0)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            "color: rgba(255,255,255,0.95); font-size: 14px; font-weight: 700;"
            "background: transparent;"
        )
        tv.addWidget(lbl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(
                "color: rgba(255,255,255,0.45); font-size: 9px; background: transparent;"
            )
            tv.addWidget(sub)

        hbox.addWidget(title_col)
        hbox.addStretch()

        if lr.logo_path and lr.logo_path.is_file():
            logo = QLabel()
            pix = QPixmap(str(lr.logo_path)).scaledToHeight(
                32, Qt.TransformationMode.SmoothTransformation
            )
            logo.setPixmap(pix)
            logo.setStyleSheet("background: transparent;")
            hbox.addWidget(logo)

        return container

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def closeEvent(self, event):
        QApplication.quit()
        event.accept()

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu {background:#1a1a1a; color:#eee; border:1px solid #333;"
            "border-radius:6px; padding:4px;}"
            "QMenu::item:selected {background:#333; border-radius:4px;}"
        )
        action_pos  = menu.addAction("📋  Copy Position")
        menu.addSeparator()
        action_quit = menu.addAction("✕  Quit")

        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == action_pos:
            g = self.geometry()
            QApplication.clipboard().setText(
                f"--xpos {g.x()} --ypos {g.y()} --width {g.width()} --height {g.height()}"
            )
        elif chosen == action_quit:
            QApplication.quit()