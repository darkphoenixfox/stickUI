"""
stickui.ui.window
~~~~~~~~~~~~~~~~~
Borderless overlay window with:
- Cover-scaled background image
- Floating logo overlay
- Invisible settings button in bottom-right corner
- Auto-reload on config file changes
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QColor, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow,
    QMenu, QPushButton, QVBoxLayout, QWidget,
)

from ..core.config import ConfigLoader
from ..core.layout import LayoutResult
from ..core.stick import StickLayout
from ..core.watcher import ConfigWatcher, watched_paths
from .background import BackgroundWidget
from .panel import ControlPanel
from .settings_dialog import SettingsDialog


# Size of the invisible corner hit area in pixels
_CORNER_BTN_SIZE = 20


class OverlayWindow(QMainWindow):

    def __init__(
        self,
        layout_result: LayoutResult,
        cfg: ConfigLoader,
        stick_layout: Optional[StickLayout] = None,
        reload_callback: Optional[Callable] = None,
        x: int = 100,
        y: int = 100,
        width: int = 620,
        height: int = 280,
        opacity: float = 0.92,
        auto_hide_seconds: int = 0,
    ) -> None:
        super().__init__()
        self._drag_pos: Optional[QPoint] = None
        self._cfg = cfg
        self._lr  = layout_result
        self._reload_callback = reload_callback
        self._logo_label: Optional[QLabel] = None
        self._corner_btn: Optional[QPushButton] = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(opacity)
        self.setGeometry(x, y, width, height)
        self.setMinimumSize(300, 150)

        self._bg = BackgroundWidget(self)
        self._bg.setObjectName("centralWidget")
        self.setCentralWidget(self._bg)

        self._build_ui(layout_result, stick_layout)

        self._watcher = self._setup_watcher(cfg)

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, QApplication.quit)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        if auto_hide_seconds > 0:
            QTimer.singleShot(auto_hide_seconds * 1000, QApplication.quit)

    # ── Build / rebuild UI ──────────────────────────────────────────────────

    def _build_ui(
        self,
        lr: LayoutResult,
        stick_layout: Optional[StickLayout] = None,
    ) -> None:
        if self._bg.layout():
            while self._bg.layout().count():
                item = self._bg.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(self._bg.layout())

        self._logo_label  = None
        self._corner_btn  = None

        bg_path = str(lr.background_path) if lr.background_path else None
        self._bg.set_image(bg_path)
        self._bg.set_panel_color(lr.panel_color)
        self._bg.setStyleSheet("QWidget#centralWidget { border-radius: 14px; }")

        root = QVBoxLayout(self._bg)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(4)

        header = self._build_header(lr)
        if header:
            root.addWidget(header)

        panel = ControlPanel(lr, stick_layout)
        root.addWidget(panel, stretch=1)

        self._place_logo(lr)
        self._place_corner_btn()

    def reload(
        self,
        layout_result: LayoutResult,
        cfg: ConfigLoader,
        stick_layout: Optional[StickLayout] = None,
    ) -> None:
        self._cfg = cfg
        self._lr  = layout_result
        self._build_ui(layout_result, stick_layout)
        self._watcher.set_paths(self._config_paths(cfg))

        win = cfg.window
        g = self.geometry()
        self.setGeometry(
            win.get("xpos",   g.x()),
            win.get("ypos",   g.y()),
            win.get("width",  g.width()),
            win.get("height", g.height()),
        )
        self.setWindowOpacity(win.get("opacity", self.windowOpacity()))
        self.update()

    # ── Invisible corner settings button ────────────────────────────────────

    def _place_corner_btn(self) -> None:
        s = _CORNER_BTN_SIZE
        btn = QPushButton("", self._bg)
        btn.setFixedSize(s, s)
        btn.setCursor(Qt.CursorShape.SizeAllCursor)
        btn.setToolTip("Settings")
        btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent;"
            "  border: none;"
            "}"
            "QPushButton:hover {"
            f" background: rgba(255,255,255,0.08);"
            "  border-radius: 4px;"
            "}"
        )
        btn.clicked.connect(self._open_settings)
        self._corner_btn = btn
        self._reposition_corner_btn()
        btn.raise_()
        btn.show()

    def _reposition_corner_btn(self) -> None:
        if self._corner_btn:
            s = _CORNER_BTN_SIZE
            self._corner_btn.move(
                self._bg.width()  - s - 4,
                self._bg.height() - s - 4,
            )

    def _open_settings(self) -> None:
        def on_apply(values: dict) -> None:
            # Apply immediately to the live window
            self.setGeometry(
                values["xpos"], values["ypos"],
                values["width"], values["height"],
            )
            self.setWindowOpacity(values["opacity"])
            # Trigger a full reload so the watcher picks up the new config
            if self._reload_callback:
                self._reload_callback()

        dlg = SettingsDialog(
            config_path      = self._cfg.global_config_path,
            current_geometry = self.geometry(),
            current_opacity  = self.windowOpacity(),
            on_apply         = on_apply,
            parent           = self,
        )
        dlg.exec()

    # ── File watcher ────────────────────────────────────────────────────────

    def _config_paths(self, cfg: ConfigLoader):
        game_toml  = (cfg.system_dir_path / f"{cfg.game}.toml") if cfg.game else None
        stick_name = cfg._system_cfg.get("system", {}).get("stick", "default")
        stick_toml = Path("sticks") / f"{stick_name}.toml"
        return watched_paths(
            config_toml = cfg.global_config_path,
            system_toml = cfg.system_dir_path / "system.toml",
            game_toml   = game_toml,
            stick_toml  = stick_toml,
        )

    def _setup_watcher(self, cfg: ConfigLoader) -> ConfigWatcher:
        watcher = ConfigWatcher(self._config_paths(cfg), parent=self)
        watcher.changed.connect(self._on_config_changed)
        return watcher

    def _on_config_changed(self) -> None:
        if hasattr(self, "_reload_timer"):
            self._reload_timer.stop()
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self._trigger_reload)
        self._reload_timer.start(300)

    def _trigger_reload(self) -> None:
        if self._reload_callback:
            self._reload_callback()

    # ── Header ──────────────────────────────────────────────────────────────

    def _build_header(self, lr: LayoutResult) -> Optional[QWidget]:
        display = self._cfg.display
        if not display.get("show_title", True):
            return None

        title    = lr.game_name or lr.system_name
        subtitle = lr.system_name if (
            lr.game_name and display.get("show_system_name", True)
        ) else ""

        if not title:
            return None

        title_font_size = int(display.get("title_font_size", 14))
        sub_font_size   = int(display.get("subtitle_font_size", 9))

        container = QWidget()
        container.setFixedHeight(36)
        container.setStyleSheet("background: transparent;")
        hbox = QHBoxLayout(container)
        hbox.setContentsMargins(4, 0, 4, 0)

        title_col = QWidget()
        title_col.setStyleSheet("background: transparent;")
        tv = QVBoxLayout(title_col)
        tv.setContentsMargins(0, 0, 0, 0)
        tv.setSpacing(0)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: rgba(255,255,255,0.95); font-size: {title_font_size}px;"
            f"font-weight: 700; background: transparent;"
        )
        tv.addWidget(lbl)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(
                f"color: rgba(255,255,255,0.45); font-size: {sub_font_size}px;"
                f"background: transparent;"
            )
            tv.addWidget(sub)

        hbox.addWidget(title_col)
        hbox.addStretch()
        return container

    # ── Logo overlay ────────────────────────────────────────────────────────

    def _place_logo(self, lr: LayoutResult) -> None:
        if not (lr.logo_path and lr.logo_path.is_file()):
            return

        display     = self._cfg.display
        logo_height = int(display.get("logo_height", 48))
        logo_y      = int(display.get("logo_y", 8))
        logo_x_cfg  = int(display.get("logo_x", -1))
        logo_margin = int(display.get("logo_margin", 12))

        pix = QPixmap(str(lr.logo_path)).scaledToHeight(
            logo_height, Qt.TransformationMode.SmoothTransformation
        )

        lbl = QLabel(self._bg)
        lbl.setPixmap(pix)
        lbl.setStyleSheet("background: transparent;")
        lbl.setFixedSize(pix.width(), pix.height())

        lx = logo_x_cfg if logo_x_cfg >= 0 else self.width() - pix.width() - logo_margin
        lbl.move(lx, logo_y)
        lbl.raise_()
        lbl.show()
        self._logo_label = lbl

    # ── Resize ──────────────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reposition auto-aligned logo
        if self._logo_label:
            display     = self._cfg.display
            logo_x_cfg  = int(display.get("logo_x", -1))
            logo_margin = int(display.get("logo_margin", 12))
            logo_y      = int(display.get("logo_y", 8))
            if logo_x_cfg < 0:
                lx = self.width() - self._logo_label.width() - logo_margin
                self._logo_label.move(lx, logo_y)
        # Reposition corner button
        self._reposition_corner_btn()

    # ── Drag ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def closeEvent(self, event):
        QApplication.quit()
        event.accept()

    # ── Context menu ────────────────────────────────────────────────────────

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu {background:#1a1a1a; color:#eee; border:1px solid #333;"
            "border-radius:6px; padding:4px;}"
            "QMenu::item:selected {background:#333; border-radius:4px;}"
        )
        action_settings = menu.addAction("⚙️  Settings")
        action_pos      = menu.addAction("📋  Copy Position")
        action_reload   = menu.addAction("🔄  Reload Now")
        menu.addSeparator()
        action_quit     = menu.addAction("✕  Quit")

        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == action_settings:
            self._open_settings()
        elif chosen == action_pos:
            g = self.geometry()
            QApplication.clipboard().setText(
                f"--xpos {g.x()} --ypos {g.y()} "
                f"--width {g.width()} --height {g.height()}"
            )
        elif chosen == action_reload:
            self._trigger_reload()
        elif chosen == action_quit:
            QApplication.quit()