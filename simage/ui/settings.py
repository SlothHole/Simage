import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from simage.utils.paths import resolve_repo_path


class SettingsTab(QWidget):
    def __init__(self, parent=None, gallery=None, batch_tab=None) -> None:
        super().__init__(parent)
        self.gallery = gallery
        self.batch_tab = batch_tab

        layout = QVBoxLayout(self)

        header = QLabel("Maintenance and setup tools (no terminal required).")
        header.setWordWrap(True)
        layout.addWidget(header)

        env_group = QGroupBox("Environment")
        env_layout = QVBoxLayout(env_group)

        self.create_venv_btn = QPushButton("Create .venv (if missing)")
        self.create_venv_btn.clicked.connect(self.create_venv)
        env_layout.addLayout(self._with_help(
            self.create_venv_btn,
            "Create a local virtual environment in .venv.",
        ))

        self.install_deps_btn = QPushButton("Install or update UI dependencies")
        self.install_deps_btn.clicked.connect(self.install_dependencies)
        env_layout.addLayout(self._with_help(
            self.install_deps_btn,
            "Install UI requirements from simage/ui/requirements.txt.",
        ))

        self.restart_ui_btn = QPushButton("Restart UI")
        self.restart_ui_btn.clicked.connect(self.restart_ui)
        env_layout.addLayout(self._with_help(
            self.restart_ui_btn,
            "Restart the UI using the current Python environment.",
        ))

        layout.addWidget(env_group)

        pipeline_group = QGroupBox("Pipeline")
        pipeline_layout = QVBoxLayout(pipeline_group)

        row1 = QHBoxLayout()
        self.run_exif_btn = QPushButton("Run EXIF scan")
        self.run_exif_btn.clicked.connect(self.run_exif_scan)
        row1.addWidget(self.run_exif_btn)
        row1.addWidget(self._help_button("Extract raw EXIF metadata into out/exif_raw.jsonl."))

        self.run_ingest_btn = QPushButton("Run ingest")
        self.run_ingest_btn.clicked.connect(self.run_ingest)
        row1.addWidget(self.run_ingest_btn)
        row1.addWidget(self._help_button("Normalize EXIF into records.csv/jsonl and images.db."))
        pipeline_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.run_resources_btn = QPushButton("Run resources")
        self.run_resources_btn.clicked.connect(self.run_resources)
        row2.addWidget(self.run_resources_btn)
        row2.addWidget(self._help_button("Parse workflow_json into the resources table."))

        self.run_resolve_btn = QPushButton("Run resolve")
        self.run_resolve_btn.clicked.connect(self.run_resolve)
        row2.addWidget(self.run_resolve_btn)
        row2.addWidget(self._help_button("Resolve resource references using local mappings."))
        pipeline_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.run_all_btn = QPushButton("Run all (ingest + resources + resolve)")
        self.run_all_btn.clicked.connect(self.run_all)
        row3.addWidget(self.run_all_btn)
        row3.addWidget(self._help_button("Run ingest, resources, and resolve in sequence."))

        self.refresh_pipeline_btn = QPushButton("Refresh pipeline (EXIF + all)")
        self.refresh_pipeline_btn.clicked.connect(self.refresh_pipeline)
        row3.addWidget(self.refresh_pipeline_btn)
        row3.addWidget(self._help_button("Run EXIF scan then the full pipeline."))
        pipeline_layout.addLayout(row3)

        layout.addWidget(pipeline_group)
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
