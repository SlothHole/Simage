import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QColorDialog,
    QFontDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from simage.utils.paths import resolve_repo_path
from .theme import (
    DEFAULT_THEME,
    apply_font,
    apply_theme,
    custom_theme_from_settings,
    load_ui_settings,
    save_ui_settings,
    theme_names,
)


class SettingsTab(QWidget):
    def __init__(self, parent=None, gallery=None, batch_tab=None) -> None:
        super().__init__(parent)
        self.gallery = gallery
        self.batch_tab = batch_tab

        layout = QVBoxLayout(self)
        self._apply_page_layout(layout)

        header = QLabel("Maintenance and setup tools (no terminal required).")
        header.setWordWrap(True)
        layout.addWidget(header)

        display_group = QGroupBox("Display")
        display_layout = QVBoxLayout(display_group)
        self._apply_section_layout(display_layout)
        self._ui_settings = load_ui_settings()
        self._color_buttons = {}
        self._display_ready = False

        theme_row = QHBoxLayout()
        theme_label = QLabel("Theme")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(theme_names())
        current_theme = self._ui_settings.get("theme", DEFAULT_THEME)
        if current_theme in theme_names():
            self.theme_combo.setCurrentText(current_theme)
        theme_row.addWidget(theme_label)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch(1)
        theme_row_widget = QWidget()
        theme_row_widget.setLayout(theme_row)
        display_layout.addLayout(self._with_help(
            theme_row_widget,
            "Adjust the UI theme to reduce eye strain.",
        ))

        font_row = QHBoxLayout()
        font_label = QLabel("Font")
        self.font_button = QPushButton("Choose font")
        self._standard_button(self.font_button)
        self.font_button.clicked.connect(self.choose_font)
        self.font_preview = QLabel("")
        font_row.addWidget(font_label)
        font_row.addWidget(self.font_button)
        font_row.addWidget(self.font_preview)
        font_row.addStretch(1)
        font_row_widget = QWidget()
        font_row_widget.setLayout(font_row)
        display_layout.addLayout(self._with_help(
            font_row_widget,
            "Pick a UI font and size.",
        ))

        custom_group = QGroupBox("Custom Colors")
        custom_layout = QVBoxLayout(custom_group)
        self._apply_section_layout(custom_layout)
        grid = QGridLayout()
        row = 0
        for label_text, section, key in self._custom_color_entries():
            label = QLabel(label_text)
            button = QPushButton()
            self._standard_button(button)
            button.clicked.connect(lambda _, s=section, k=key: self._pick_custom_color(s, k))
            grid.addWidget(label, row, 0)
            grid.addWidget(button, row, 1)
            self._color_buttons[(section, key)] = button
            row += 1
        custom_layout.addLayout(grid)
        display_layout.addWidget(custom_group)

        self.reset_display_btn = QPushButton("Reset display settings")
        self._standard_button(self.reset_display_btn)
        self.reset_display_btn.clicked.connect(self.reset_display_settings)
        display_layout.addLayout(self._with_help(
            self.reset_display_btn,
            "Restore the default display theme.",
        ))

        self._update_font_preview()
        self._refresh_custom_colors()
        self._display_ready = True
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        env_group = QGroupBox("Environment")
        env_layout = QVBoxLayout(env_group)
        self._apply_section_layout(env_layout)

        self.create_venv_btn = QPushButton("Create .venv (if missing)")
        self._standard_button(self.create_venv_btn)
        self.create_venv_btn.clicked.connect(self.create_venv)
        env_layout.addLayout(self._with_help(
            self.create_venv_btn,
            "Create a local virtual environment in .venv.",
        ))

        self.install_deps_btn = QPushButton("Install or update UI dependencies")
        self._standard_button(self.install_deps_btn)
        self.install_deps_btn.clicked.connect(self.install_dependencies)
        env_layout.addLayout(self._with_help(
            self.install_deps_btn,
            "Install UI requirements from simage/ui/requirements.txt.",
        ))

        self.restart_ui_btn = QPushButton("Restart UI")
        self._standard_button(self.restart_ui_btn)
        self.restart_ui_btn.clicked.connect(self.restart_ui)
        env_layout.addLayout(self._with_help(
            self.restart_ui_btn,
            "Restart the UI using the current Python environment.",
        ))

        pipeline_group = QGroupBox("Pipeline")
        pipeline_layout = QVBoxLayout(pipeline_group)
        self._apply_section_layout(pipeline_layout)

        row1 = QHBoxLayout()
        self.run_exif_btn = QPushButton("Run EXIF scan")
        self._standard_button(self.run_exif_btn)
        self.run_exif_btn.clicked.connect(self.run_exif_scan)
        row1.addWidget(self.run_exif_btn)
        row1.addWidget(self._help_button("Extract raw EXIF metadata into out/exif_raw.jsonl."))

        self.run_ingest_btn = QPushButton("Run ingest")
        self._standard_button(self.run_ingest_btn)
        self.run_ingest_btn.clicked.connect(self.run_ingest)
        row1.addWidget(self.run_ingest_btn)
        row1.addWidget(self._help_button("Normalize EXIF into records.csv/jsonl and images.db."))
        pipeline_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.run_resources_btn = QPushButton("Run resources")
        self._standard_button(self.run_resources_btn)
        self.run_resources_btn.clicked.connect(self.run_resources)
        row2.addWidget(self.run_resources_btn)
        row2.addWidget(self._help_button("Parse workflow_json into the resources table."))

        self.run_resolve_btn = QPushButton("Run resolve")
        self._standard_button(self.run_resolve_btn)
        self.run_resolve_btn.clicked.connect(self.run_resolve)
        row2.addWidget(self.run_resolve_btn)
        row2.addWidget(self._help_button("Resolve resource references using local mappings."))
        pipeline_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.run_all_btn = QPushButton("Run all (ingest + resources + resolve)")
        self._standard_button(self.run_all_btn)
        self.run_all_btn.clicked.connect(self.run_all)
        row3.addWidget(self.run_all_btn)
        row3.addWidget(self._help_button("Run ingest, resources, and resolve in sequence."))

        self.refresh_pipeline_btn = QPushButton("Refresh pipeline (EXIF + all)")
        self._standard_button(self.refresh_pipeline_btn)
        self.refresh_pipeline_btn.clicked.connect(self.refresh_pipeline)
        row3.addWidget(self.refresh_pipeline_btn)
        row3.addWidget(self._help_button("Run EXIF scan then the full pipeline."))
        pipeline_layout.addLayout(row3)

        self.tabs = QTabWidget()
        display_tab = QWidget()
        display_tab_layout = QVBoxLayout(display_tab)
        self._apply_tab_layout(display_tab_layout)
        display_tab_layout.addWidget(display_group)
        display_tab_layout.addStretch(1)

        env_tab = QWidget()
        env_tab_layout = QVBoxLayout(env_tab)
        self._apply_tab_layout(env_tab_layout)
        env_tab_layout.addWidget(env_group)
        env_tab_layout.addStretch(1)

        pipeline_tab = QWidget()
        pipeline_tab_layout = QVBoxLayout(pipeline_tab)
        self._apply_tab_layout(pipeline_tab_layout)
        pipeline_tab_layout.addWidget(pipeline_group)
        pipeline_tab_layout.addStretch(1)

        self.tabs.addTab(display_tab, "Display")
        self.tabs.addTab(env_tab, "Environment")
        self.tabs.addTab(pipeline_tab, "Pipeline")
        layout.addWidget(self.tabs)
        layout.addStretch(1)

    def _help_button(self, text: str) -> QToolButton:
        btn = QToolButton()
        btn.setText("?")
        btn.setAutoRaise(True)
        btn.setToolTip(text)
        btn.setCursor(Qt.WhatsThisCursor)
        btn.setFixedSize(16, 16)
        return btn

    def _with_help(self, widget: QWidget, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(widget)
        row.addWidget(self._help_button(text))
        row.addStretch(1)
        return row

    def _standard_button(self, button: QPushButton) -> None:
        button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def _apply_page_layout(self, layout: QVBoxLayout) -> None:
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

    def _apply_section_layout(self, layout: QVBoxLayout) -> None:
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

    def _apply_tab_layout(self, layout: QVBoxLayout) -> None:
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

    def _on_theme_changed(self, theme_name: str) -> None:
        if not self._display_ready:
            return
        app = QApplication.instance()
        if not app:
            return
        applied = apply_theme(app, theme_name)
        if applied != theme_name:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText(applied)
            self.theme_combo.blockSignals(False)
        settings = load_ui_settings()
        settings["theme"] = applied
        save_ui_settings(settings)
        self._ui_settings = settings
        apply_font(app, settings)
        self._refresh_theme_targets()

    def reset_display_settings(self) -> None:
        self._ui_settings = load_ui_settings()
        self._ui_settings["theme"] = DEFAULT_THEME
        self._ui_settings["font_family"] = ""
        self._ui_settings["font_size"] = 0
        self._ui_settings["custom_theme"] = {"palette": {}, "thumb": {}}
        save_ui_settings(self._ui_settings)
        app = QApplication.instance()
        if app:
            apply_theme(app, DEFAULT_THEME)
            apply_font(app, self._ui_settings)
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText(DEFAULT_THEME)
        self.theme_combo.blockSignals(False)
        self._update_font_preview()
        self._refresh_custom_colors()
        self._refresh_theme_targets()

    def _refresh_theme_targets(self) -> None:
        if self.gallery and hasattr(self.gallery, "grid"):
            self.gallery.grid.refresh_theme()

    def choose_font(self) -> None:
        app = QApplication.instance()
        if not app:
            return
        current = app.font()
        result = QFontDialog.getFont(current, self, "Choose UI Font")
        if not isinstance(result, tuple) or len(result) != 2:
            return
        if isinstance(result[0], bool):
            ok, font = result
        else:
            font, ok = result
        if not ok or not font:
            return
        settings = load_ui_settings()
        settings["font_family"] = font.family()
        settings["font_size"] = font.pointSize()
        save_ui_settings(settings)
        self._ui_settings = settings
        apply_font(app, settings)
        self._update_font_preview()

    def _update_font_preview(self) -> None:
        family = self._ui_settings.get("font_family") or "System Default"
        size = int(self._ui_settings.get("font_size") or 0)
        if size > 0 and family != "System Default":
            text = f"{family} {size}pt"
        elif size > 0:
            text = f"System Default {size}pt"
        else:
            text = family
        self.font_preview.setText(text)

    def _custom_color_entries(self) -> list[tuple[str, str, str]]:
        return [
            ("Window background", "palette", "window"),
            ("Window text", "palette", "window_text"),
            ("Panel background", "palette", "panel_bg"),
            ("Base background", "palette", "base"),
            ("Alternate background", "palette", "alternate_base"),
            ("Label background", "palette", "label_bg"),
            ("Text", "palette", "text"),
            ("Accent", "palette", "highlight"),
            ("Accent text", "palette", "highlighted_text"),
            ("Button", "palette", "button"),
            ("Button text", "palette", "button_text"),
            ("Link", "palette", "link"),
            ("Placeholder text", "palette", "placeholder"),
            ("Border", "palette", "border"),
            ("Button hover", "palette", "button_hover"),
            ("Button pressed", "palette", "button_pressed"),
            ("Tab inactive", "palette", "tab_inactive"),
            ("Tab active", "palette", "tab_active"),
            ("Scrollbar", "palette", "scrollbar"),
            ("Scrollbar handle", "palette", "scrollbar_handle"),
            ("Scrollbar handle hover", "palette", "scrollbar_handle_hover"),
            ("Tooltip background", "palette", "tool_tip_base"),
            ("Tooltip text", "palette", "tool_tip_text"),
            ("Thumbnail background", "thumb", "bg"),
            ("Thumbnail border", "thumb", "border"),
            ("Selected thumbnail background", "thumb", "selected_bg"),
            ("Selected thumbnail border", "thumb", "selected_border"),
        ]

    def _refresh_custom_colors(self) -> None:
        resolved = custom_theme_from_settings(self._ui_settings)
        for (section, key), button in self._color_buttons.items():
            color = resolved.get(section, {}).get(key, "")
            self._set_color_button(button, color)

    def _pick_custom_color(self, section: str, key: str) -> None:
        settings = load_ui_settings()
        resolved = custom_theme_from_settings(settings)
        current = resolved.get(section, {}).get(key, "")
        initial = QColor(current) if current else QColor("#ffffff")
        picked = QColorDialog.getColor(initial, self, "Pick Color")
        if not picked.isValid():
            return
        color_hex = picked.name()
        custom = settings.setdefault("custom_theme", {"palette": {}, "thumb": {}})
        custom_section = custom.setdefault(section, {})
        custom_section[key] = color_hex
        settings["theme"] = "Custom"
        save_ui_settings(settings)
        self._ui_settings = settings
        self._set_color_button(self._color_buttons[(section, key)], color_hex)
        if self.theme_combo.currentText() != "Custom":
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText("Custom")
            self.theme_combo.blockSignals(False)
        app = QApplication.instance()
        if app:
            apply_theme(app, "Custom")
        self._refresh_theme_targets()

    def _set_color_button(self, button: QPushButton, color_hex: str) -> None:
        if not color_hex:
            color_hex = "#ffffff"
        button.setText(color_hex)
        button.setStyleSheet(self._color_button_style(color_hex))

    def _color_button_style(self, color_hex: str) -> str:
        color = QColor(color_hex)
        if not color.isValid():
            return ""
        r, g, b, _ = color.getRgb()
        luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b)
        text = "#000000" if luminance > 160 else "#ffffff"
        return f"background-color: {color_hex}; color: {text};"

    def _repo_root(self) -> Path:
        return resolve_repo_path(".", must_exist=True, allow_absolute=False)

    def _venv_python(self) -> Path | None:
        candidates = [
            resolve_repo_path(".venv/Scripts/python.exe", must_exist=False, allow_absolute=False),
            resolve_repo_path(".venv/bin/python", must_exist=False, allow_absolute=False),
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _python_for_actions(self) -> str:
        venv_python = self._venv_python()
        return str(venv_python) if venv_python else sys.executable

    def _find_exiftool(self) -> Path | None:
        candidates = [
            resolve_repo_path("exiftool-13.45_64/ExifTool.exe", must_exist=False, allow_absolute=False),
            resolve_repo_path("exiftool-13.45_64/exiftool", must_exist=False, allow_absolute=False),
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _run_command(
        self,
        args: list[str],
        title: str,
        success_message: str | None = None,
        *,
        show_error: bool = True,
    ) -> bool:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = subprocess.run(
                args,
                cwd=str(self._repo_root()),
                capture_output=True,
                text=True,
            )
        finally:
            QApplication.restoreOverrideCursor()

        if result.returncode != 0:
            details = (result.stderr or result.stdout or "").strip()
            if not details:
                details = "Command failed."
            if show_error:
                QMessageBox.critical(self, title, details)
            return False

        if success_message:
            QMessageBox.information(self, title, success_message)
        return True

    def _ensure_pip(self, python_exe: str) -> bool:
        ok = self._run_command([python_exe, "-m", "pip", "--version"], "pip", None, show_error=False)
        if ok:
            return True
        if not self._run_command([python_exe, "-m", "ensurepip", "--upgrade"], "ensurepip", None):
            return False
        return self._run_command([python_exe, "-m", "pip", "--version"], "pip", None, show_error=False)

    def _reload_gallery(self) -> None:
        if self.gallery and hasattr(self.gallery, "reload_records"):
            self.gallery.reload_records()

    def create_venv(self) -> None:
        venv_python = self._venv_python()
        if venv_python:
            QMessageBox.information(self, "Create .venv", ".venv already exists.")
            return
        if not self._run_command(
            [sys.executable, "-m", "venv", ".venv"],
            "Create .venv",
            "Created .venv. Restart the app to use it.",
        ):
            return

    def install_dependencies(self) -> None:
        python_exe = self._python_for_actions()
        if not self._ensure_pip(python_exe):
            QMessageBox.critical(self, "Install Dependencies", "pip is not available for this Python.")
            return
        req_path = resolve_repo_path("simage/ui/requirements.txt", must_exist=False, allow_absolute=False)
        ok = self._run_command(
            [python_exe, "-m", "pip", "install", "-r", str(req_path)],
            "Install Dependencies",
            "Dependencies installed. Restart the app if needed.",
        )
        if not ok:
            return

    def restart_ui(self) -> None:
        python_exe = self._python_for_actions()
        try:
            subprocess.Popen(
                [python_exe, "-m", "simage.ui.app"],
                cwd=str(self._repo_root()),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Restart UI", f"Failed to restart UI: {exc}")
            return
        QApplication.quit()

    def run_exif_scan(self) -> None:
        python_exe = self._python_for_actions()
        args = [
            python_exe,
            "-m",
            "simage.core.exif",
            "--input",
            "Input",
            "--out",
            "out/exif_raw.jsonl",
        ]
        exiftool_path = self._find_exiftool()
        if exiftool_path:
            args += ["--exiftool", str(exiftool_path)]
        self._run_command(args, "EXIF Scan", "EXIF scan complete.")

    def run_ingest(self) -> None:
        python_exe = self._python_for_actions()
        ok = self._run_command(
            [
                python_exe,
                "-m",
                "simage",
                "ingest",
                "--in",
                "out/exif_raw.jsonl",
                "--db",
                "out/images.db",
                "--schema",
                "simage/data/schema.sql",
                "--jsonl",
                "out/records.jsonl",
                "--csv",
                "out/records.csv",
            ],
            "Ingest",
            "Ingest complete.",
        )
        if ok:
            self._reload_gallery()

    def run_resources(self) -> None:
        python_exe = self._python_for_actions()
        self._run_command(
            [
                python_exe,
                "-m",
                "simage",
                "resources",
                "--db",
                "out/images.db",
            ],
            "Resources",
            "Resources parse complete.",
        )

    def run_resolve(self) -> None:
        python_exe = self._python_for_actions()
        self._run_command(
            [
                python_exe,
                "-m",
                "simage",
                "resolve",
                "--db",
                "out/images.db",
            ],
            "Resolve",
            "Resolve complete.",
        )

    def run_all(self) -> None:
        python_exe = self._python_for_actions()
        ok = self._run_command(
            [
                python_exe,
                "-m",
                "simage",
                "all",
                "--in",
                "out/exif_raw.jsonl",
                "--db",
                "out/images.db",
                "--schema",
                "simage/data/schema.sql",
                "--jsonl",
                "out/records.jsonl",
                "--csv",
                "out/records.csv",
            ],
            "Run All",
            "Pipeline complete.",
        )
        if ok:
            self._reload_gallery()

    def refresh_pipeline(self) -> None:
        if self.batch_tab and hasattr(self.batch_tab, "refresh_pipeline"):
            self.batch_tab.refresh_pipeline()
            return
        self.run_exif_scan()
        self.run_all()
