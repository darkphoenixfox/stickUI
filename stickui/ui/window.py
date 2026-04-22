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
from ..core.game_writer import save_game_toml
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

        self._edit_mode = False
        self._edit_bar: Optional[QWidget] = None
        self._watcher = self._setup_watcher(cfg)

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self._escape_pressed)
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
        self._bg.set_dim(self._cfg.background_dim)
        self._bg.setStyleSheet("QWidget#centralWidget { border-radius: 14px; }")

        root = QVBoxLayout(self._bg)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(4)

        header = self._build_header(lr)
        if header:
            root.addWidget(header)

        self._panel = ControlPanel(lr, stick_layout)
        self.sl = stick_layout   # keep reference for save
        root.addWidget(self._panel, stretch=1)

        self._place_logo(lr)
        self._place_corner_btn()
        self._place_edit_btn()

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
            if "background_dim" in values:
                self._bg.set_dim(values["background_dim"])
            # Trigger a full reload so the watcher picks up the new config
            if self._reload_callback:
                self._reload_callback()

        dlg = SettingsDialog(
            config_path      = self._cfg.global_config_path,
            current_geometry = self.geometry(),
            current_opacity  = self.windowOpacity(),
            on_apply         = on_apply,
            cfg              = self._cfg,
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
        # Delete any existing logo label first to prevent ghost rendering
        if self._logo_label:
            self._logo_label.deleteLater()
            self._logo_label = None
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

    def _reposition_edit_btn(self) -> None:
        if hasattr(self, '_edit_btn') and self._edit_btn:
            s = 20
            self._edit_btn.move(4, self._bg.height() - s - 4)

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
        # Reposition corner buttons
        self._reposition_corner_btn()
        self._reposition_edit_btn()

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

    def _escape_pressed(self):
        if self._edit_mode:
            self._set_edit_mode(False)
        else:
            QApplication.quit()

    # ── Edit mode ───────────────────────────────────────────────────────────

    def _place_edit_btn(self) -> None:
        s = 20
        btn = QPushButton("", self._bg)
        btn.setFixedSize(s, s)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip("Edit layout")
        btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background: rgba(255,220,50,0.12); border-radius: 4px; }"
        )
        btn.clicked.connect(lambda: self._set_edit_mode(not self._edit_mode))
        btn.raise_()
        btn.show()
        self._edit_btn = btn
        self._reposition_edit_btn()

    def _set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = enabled
        if hasattr(self, '_panel'):
            self._panel.set_edit_mode(
                enabled,
                on_slot_changed=self._on_slot_changed,
            )
        if enabled:
            self._show_edit_bar()
        else:
            self._hide_edit_bar()

    def _on_slot_changed(self) -> None:
        """Called when any slot is edited — mark unsaved changes."""
        if hasattr(self, '_status_lbl') and self._status_lbl:
            self._status_lbl.setText("● Unsaved changes")
            self._status_lbl.setStyleSheet("color: #ffcc44; font-size: 10px; background: transparent;")
        # Keep edit bar on top after panel repaints
        if self._edit_bar:
            self._edit_bar.raise_()

    def _show_edit_bar(self) -> None:
        bar = QWidget(self._bg)
        bar.setStyleSheet(
            "background: rgba(20,20,40,0.92);"
            "border-top: 1px solid rgba(255,220,50,0.3);"
            "border-radius: 0px 0px 14px 14px;"
        )
        bar_h = 36
        bar.setGeometry(0, self._bg.height() - bar_h, self._bg.width(), bar_h)

        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(8)

        mode_lbl = QLabel("✏  Edit Mode — click any button to edit")
        mode_lbl.setStyleSheet("color: #ffcc44; font-size: 11px; background: transparent;")
        row.addWidget(mode_lbl)
        row.addStretch()

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #aaaacc; font-size: 10px; background: transparent;")
        row.addWidget(self._status_lbl)

        save_btn = QPushButton("💾  Save")
        save_btn.setFixedHeight(24)
        save_btn.setStyleSheet(
            "QPushButton { background: #226622; color: #fff; border: 1px solid #44aa44;"
            "border-radius: 5px; padding: 0 10px; font-size: 11px; }"
            "QPushButton:hover { background: #338833; }"
        )
        save_btn.clicked.connect(self._save_game_toml)
        row.addWidget(save_btn)

        revert_btn = QPushButton("↩  Revert")
        revert_btn.setFixedHeight(24)
        revert_btn.setStyleSheet(
            "QPushButton { background: #662222; color: #fff; border: 1px solid #aa4444;"
            "border-radius: 5px; padding: 0 10px; font-size: 11px; }"
            "QPushButton:hover { background: #883333; }"
        )
        revert_btn.clicked.connect(self._revert_edits)
        row.addWidget(revert_btn)

        done_btn = QPushButton("✓  Done")
        done_btn.setFixedHeight(24)
        done_btn.setStyleSheet(
            "QPushButton { background: #22224a; color: #ccc; border: 1px solid #444466;"
            "border-radius: 5px; padding: 0 10px; font-size: 11px; }"
            "QPushButton:hover { background: #2e2e60; }"
        )
        done_btn.clicked.connect(lambda: self._set_edit_mode(False))
        row.addWidget(done_btn)

        bar.raise_()
        bar.show()
        self._edit_bar = bar

    def _hide_edit_bar(self) -> None:
        if self._edit_bar:
            self._edit_bar.hide()        # hide immediately
            self._edit_bar.setParent(None)  # detach from widget tree now
            self._edit_bar.deleteLater() # schedule Qt cleanup
            self._edit_bar = None
        self._status_lbl = None

    def _save_game_toml(self) -> None:
        if not self._cfg.game or not self.sl:
            return
        game_toml = self._cfg.system_dir_path / f"{self._cfg.game}.toml"
        try:
            # Stop watcher FIRST so the file write doesn't trigger a reload
            if hasattr(self, '_watcher'):
                self._watcher.set_paths([])

            save_game_toml(
                game_toml_path = game_toml,
                stick_layout   = self.sl,
                system_cfg     = self._cfg._system_cfg,
                game_cfg       = self._cfg._game_cfg,
            )
        except Exception as e:
            print(f"[stickui] Save error: {e}")
            if hasattr(self, '_watcher') and hasattr(self, '_cfg'):
                self._watcher.set_paths(self._config_paths(self._cfg))
            if hasattr(self, '_status_lbl') and self._status_lbl:
                self._status_lbl.setText("✗ Save failed")
                self._status_lbl.setStyleSheet("color: #ee4444; font-size: 10px; background: transparent;")
            return

        # Exit edit mode immediately — this destroys the bar cleanly
        self._set_edit_mode(False)

        # Re-enable watcher now that UI is in a clean state
        if hasattr(self, '_watcher') and hasattr(self, '_cfg'):
            self._watcher.set_paths(self._config_paths(self._cfg))

    def _revert_edits(self) -> None:
        """Reload from disk — discards all unsaved edits."""
        self._set_edit_mode(False)
        if self._reload_callback:
            self._reload_callback()

    # ── Context menu ────────────────────────────────────────────────────────

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu {background:#1a1a1a; color:#eee; border:1px solid #333;"
            "border-radius:6px; padding:4px;}"
            "QMenu::item:selected {background:#333; border-radius:4px;}"
        )
        action_edit     = menu.addAction("✏️  Edit Layout")
        action_settings = menu.addAction("⚙️  Settings")
        action_pos      = menu.addAction("📋  Copy Position")
        action_reload   = menu.addAction("🔄  Reload Now")
        menu.addSeparator()
        action_quit     = menu.addAction("✕  Quit")

        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == action_edit:
            self._set_edit_mode(not self._edit_mode)
        elif chosen == action_settings:
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