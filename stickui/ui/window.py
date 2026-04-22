"""
controlpad.ui.window
~~~~~~~~~~~~~~~~~~~~
Borderless, always-on-top overlay window built with PyQt6.

Features
--------
* Translucent / semi-transparent background
* Background image support (system or game)
* System / game logo displayed in the top-right corner
* Drag to reposition (left-click drag)
* Right-click menu: Reload, Copy position, Quit
* ESC key quits
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QSize, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QFontDatabase, QIcon, QKeySequence,
    QPainter, QPixmap, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QMenu, QSizePolicy,
    QVBoxLayout, QWidget,
)

from ..core.layout import LayoutResult
from .panel import ControlPanel


class OverlayWindow(QMainWindow):
    """
    Frameless overlay window that displays the control layout.
    """

    def __init__(
        self,
        layout_result: LayoutResult,
        x: int = 100,
        y: int = 100,
        width: int = 800,
        height: int = 480,
        opacity: float = 0.92,
        auto_hide_seconds: int = 0,
    ) -> None:
        super().__init__()

        self._layout = layout_result
        self._drag_pos: Optional[QPoint] = None

        # ── Window flags ───────────────────────────────────────────────────
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool          # keeps it off the taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(opacity)
        self.setGeometry(x, y, width, height)
        self.setMinimumSize(320, 200)

        # ── Central widget ─────────────────────────────────────────────────
        self._central = QWidget(self)
        self._central.setObjectName("centralWidget")
        self.setCentralWidget(self._central)

        # Apply background colour / image via stylesheet
        self._apply_background(layout_result)

        # ── Main layout ────────────────────────────────────────────────────
        root_vbox = QVBoxLayout(self._central)
        root_vbox.setContentsMargins(12, 12, 12, 12)
        root_vbox.setSpacing(8)

        # Header row (logo + title)
        self._header = self._build_header(layout_result)
        root_vbox.addWidget(self._header)

        # Control panel (the actual buttons)
        self._panel = ControlPanel(layout_result)
        root_vbox.addWidget(self._panel, stretch=1)

        # ── Keyboard shortcut ──────────────────────────────────────────────
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, QApplication.quit)

        # ── Context menu ───────────────────────────────────────────────────
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # ── Auto-hide ─────────────────────────────────────────────────────
        if auto_hide_seconds > 0:
            QTimer.singleShot(auto_hide_seconds * 1000, self.close)

    # ── Background ─────────────────────────────────────────────────────────

    def _apply_background(self, lr: LayoutResult) -> None:
        panel_color = lr.panel_color

        if lr.background_path and lr.background_path.is_file():
            bg = str(lr.background_path).replace("\\", "/")
            self._central.setStyleSheet(
                f"""
                #centralWidget {{
                    background-image: url("{bg}");
                    background-repeat: no-repeat;
                    background-position: center;
                    background-size: cover;
                    border-radius: 14px;
                }}
                """
            )
        else:
            # Subtle gradient based on panel colour
            c = QColor(panel_color)
            lighter = c.lighter(140).name()
            self._central.setStyleSheet(
                f"""
                #centralWidget {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 {lighter},
                        stop:1 {panel_color}
                    );
                    border-radius: 14px;
                    border: 1px solid rgba(255,255,255,0.08);
                }}
                """
            )

    # ── Header ─────────────────────────────────────────────────────────────

    def _build_header(self, lr: LayoutResult) -> QWidget:
        container = QWidget()
        container.setFixedHeight(48)
        container.setStyleSheet("background: transparent;")

        from PyQt6.QtWidgets import QHBoxLayout
        hbox = QHBoxLayout(container)
        hbox.setContentsMargins(4, 0, 4, 0)

        # Title text
        title = lr.game_name or lr.system_name
        subtitle = lr.system_name if lr.game_name else ""

        title_widget = QWidget()
        title_widget.setStyleSheet("background: transparent;")
        tvbox = QVBoxLayout(title_widget)
        tvbox.setContentsMargins(0, 0, 0, 0)
        tvbox.setSpacing(0)

        lbl_main = QLabel(title)
        lbl_main.setStyleSheet(
            "color: rgba(255,255,255,0.95); font-size: 15px; font-weight: 700;"
            "background: transparent;"
        )
        tvbox.addWidget(lbl_main)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setStyleSheet(
                "color: rgba(255,255,255,0.5); font-size: 10px; background: transparent;"
            )
            tvbox.addWidget(lbl_sub)

        hbox.addWidget(title_widget)
        hbox.addStretch()

        # Logo (if available)
        if lr.logo_path and lr.logo_path.is_file():
            logo_lbl = QLabel()
            pix = QPixmap(str(lr.logo_path)).scaledToHeight(
                40, Qt.TransformationMode.SmoothTransformation
            )
            logo_lbl.setPixmap(pix)
            logo_lbl.setStyleSheet("background: transparent;")
            hbox.addWidget(logo_lbl)

        return container

    # ── Drag to move ───────────────────────────────────────────────────────

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

    # ── Context menu ───────────────────────────────────────────────────────

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background: #1a1a1a;
                color: #eee;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item:selected { background: #333; border-radius: 4px; }
            """
        )

        action_pos = menu.addAction("📋  Copy Position")
        menu.addSeparator()
        action_quit = menu.addAction("✕  Quit")

        chosen = menu.exec(self.mapToGlobal(pos))

        if chosen == action_pos:
            geo = self.geometry()
            QApplication.clipboard().setText(
                f"--xpos {geo.x()} --ypos {geo.y()} "
                f"--width {geo.width()} --height {geo.height()}"
            )
        elif chosen == action_quit:
            self.close()