import csv
import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from simage.utils.paths import resolve_repo_path
from .csv_edit import amend_records_csv
from .record_filter import load_records
from .scanner import IMG_EXTS
from .thumbnails import THUMB_DIR, ensure_thumbnail, thumbnail_path_for_source


class BatchTab(QWidget):
    def __init__(self, parent=None, gallery=None) -> None:
        super().__init__(parent)
        self.gallery = gallery
        self.csv_path = str(resolve_repo_path("out/records.csv", must_exist=False, allow_absolute=False))
        self.selected_images: List[str] = []

        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self._apply_page_layout(layout)

        self.info_label = QLabel("Select images in the Gallery tab, then apply batch actions here.")
        self.info_label.setWordWrap(True)
        info_row = QHBoxLayout()
        info_row.addWidget(self.info_label)
        info_row.addWidget(
            self._help_button("Batch actions apply to the images selected in Gallery.")
        )
        info_row.addStretch(1)
        layout.addLayout(info_row)

        self.selected_label = QLabel("Selected: 0")
        selected_row = QHBoxLayout()
        selected_row.addWidget(self.selected_label)
        selected_row.addWidget(
            self._help_button("Shows how many images are currently selected.")
        )
        selected_row.addStretch(1)
        layout.addLayout(selected_row)

        self.selected_list = QListWidget()
        layout.addWidget(self.selected_list)

        tag_layout = QHBoxLayout()
        self.batch_tag_input = QLineEdit()
        self.batch_tag_input.setPlaceholderText("Batch tag: tags, comma-separated")
        self.batch_tag_btn = QPushButton("Apply Batch Tags")
        self._standard_button(self.batch_tag_btn)
        self.batch_tag_btn.clicked.connect(self.apply_batch_tags)
        tag_layout.addWidget(self.batch_tag_input)
        tag_layout.addWidget(self.batch_tag_btn)
        tag_layout.addWidget(
            self._help_button("Add tags to all selected images (comma-separated).")
        )
        layout.addLayout(tag_layout)

        rename_layout = QHBoxLayout()
        self.batch_rename_input = QLineEdit()
        self.batch_rename_input.setPlaceholderText("Batch rename: base name")
        self.batch_rename_btn = QPushButton("Batch Rename")
        self._standard_button(self.batch_rename_btn)
        self.batch_rename_btn.clicked.connect(self.apply_batch_rename)
        rename_layout.addWidget(self.batch_rename_input)
        rename_layout.addWidget(self.batch_rename_btn)
        rename_layout.addWidget(
            self._help_button("Rename selected images with a base name and index.")
        )
        layout.addLayout(rename_layout)

        move_layout = QHBoxLayout()
        self.batch_move_input = QLineEdit()
        self.batch_move_input.setPlaceholderText("Batch move: target folder")
        self.batch_move_btn = QPushButton("Batch Move")
        self._standard_button(self.batch_move_btn)
        self.batch_move_btn.clicked.connect(self.apply_batch_move)
        move_layout.addWidget(self.batch_move_input)
        move_layout.addWidget(self.batch_move_btn)
        move_layout.addWidget(
            self._help_button("Move selected images to a target folder.")
        )
        layout.addLayout(move_layout)

        actions_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export Selected")
        self._standard_button(self.export_btn)
        self.export_btn.clicked.connect(self.export_selected)
        actions_layout.addWidget(self.export_btn)
        actions_layout.addWidget(
            self._help_button("Copy selected images to exported_images with JSON metadata.")
        )

        self.import_btn = QPushButton("Import Folder")
        self._standard_button(self.import_btn)
        self.import_btn.clicked.connect(self.import_folder)
        actions_layout.addWidget(self.import_btn)
        actions_layout.addWidget(
            self._help_button("Import images from a folder into Input/.")
        )

        self.refresh_btn = QPushButton("Refresh Pipeline")
        self._standard_button(self.refresh_btn)
        self.refresh_btn.clicked.connect(self.refresh_pipeline)
        actions_layout.addWidget(self.refresh_btn)
        actions_layout.addWidget(
            self._help_button("Run EXIF + full pipeline to refresh records and thumbnails.")
        )
        layout.addLayout(actions_layout)

    def _help_button(self, text):
        btn = QToolButton()
        btn.setText("?")
        btn.setAutoRaise(True)
        btn.setToolTip(text)
        btn.setCursor(Qt.WhatsThisCursor)
        btn.setFixedSize(16, 16)
        return btn

    def _standard_button(self, button: QPushButton) -> None:
        button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def _apply_page_layout(self, layout: QVBoxLayout) -> None:
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

    def set_selected_images(self, image_paths: List[str]) -> None:
        self.selected_images = image_paths
        self.selected_label.setText(f"Selected: {len(image_paths)}")
        self.selected_list.clear()
        for path in image_paths:
            self.selected_list.addItem(path)

    def _ensure_selection(self) -> bool:
        if self.selected_images:
            return True
        QMessageBox.warning(self, "No Selection", "Select images in the Gallery tab first.")
        return False

    def _reload_gallery(self) -> None:
        if self.gallery and hasattr(self.gallery, "reload_records"):
            self.gallery.reload_records()

    def apply_batch_tags(self) -> None:
        if not self._ensure_selection():
            return
        tags = [t.strip() for t in self.batch_tag_input.text().split(",") if t.strip()]
        if not tags:
            QMessageBox.warning(self, "No Tags", "Enter one or more tags.")
            return

        records = self.gallery.all_records if self.gallery else load_records(self.csv_path)
        updates = []
        for img_path in self.selected_images:
            fname = os.path.basename(img_path)
            rec = next((r for r in records if r.get("file_name") == fname), None)
            if rec:
                prompt = rec.get("prompt", "")
                prompt_tags = {t.strip() for t in str(prompt).split(",") if t.strip()}
                prompt_tags.update(tags)
                updates.append({"file_name": fname, "prompt": ", ".join(sorted(prompt_tags))})
        amend_records_csv(self.csv_path, updates, key_field="file_name")
        self._reload_gallery()

    def _update_csv_for_renames(self, rename_map: Dict[str, str]) -> None:
        if not rename_map or not os.path.exists(self.csv_path):
            return
        backup_path = self.csv_path + ".bak"
        if not os.path.exists(backup_path):
            os.replace(self.csv_path, backup_path)
        else:
            os.remove(self.csv_path)
            os.replace(backup_path, self.csv_path)
            os.replace(self.csv_path, backup_path)
        with open(backup_path, "r", encoding="utf-8", newline="") as f:
            reader = list(csv.DictReader(f))
            fieldnames = reader[0].keys() if reader else []
        for row in reader:
            old_name = row.get("file_name")
            if old_name in rename_map:
                new_name = rename_map[old_name]
                row["file_name"] = new_name
                src = row.get("source_file", "")
                if src:
                    row["source_file"] = os.path.join(os.path.dirname(src), new_name)
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                writer.writerow(row)

    def apply_batch_rename(self) -> None:
        if not self._ensure_selection():
            return
        base = self.batch_rename_input.text().strip()
        if not base:
            QMessageBox.warning(self, "Missing Name", "Enter a base name for renaming.")
            return

        rename_map: Dict[str, str] = {}
        new_paths = []
        for i, img_path in enumerate(self.selected_images):
            fname = os.path.basename(img_path)
            ext = os.path.splitext(fname)[1]
            new_name = f"{base}_{i+1}{ext}"
            new_path = os.path.join(os.path.dirname(img_path), new_name)
            if os.path.exists(img_path):
                os.rename(img_path, new_path)
                old_thumb = thumbnail_path_for_source(img_path, THUMB_DIR)
                if os.path.exists(old_thumb):
                    try:
                        os.remove(old_thumb)
                    except Exception:
                        pass
                ensure_thumbnail(new_path, THUMB_DIR)
            rename_map[fname] = new_name
            new_paths.append(new_path)

        self._update_csv_for_renames(rename_map)
        self.set_selected_images(new_paths)
        self._reload_gallery()

    def apply_batch_move(self) -> None:
        if not self._ensure_selection():
            return
        target = self.batch_move_input.text().strip()
        if not target:
            QMessageBox.warning(self, "Missing Target", "Enter a target folder.")
            return

        os.makedirs(target, exist_ok=True)
        new_paths = []
        for img_path in self.selected_images:
            fname = os.path.basename(img_path)
            new_path = os.path.join(target, fname)
            if os.path.exists(img_path) and not os.path.exists(new_path):
                os.rename(img_path, new_path)
                old_thumb = thumbnail_path_for_source(img_path, THUMB_DIR)
                if os.path.exists(old_thumb):
                    try:
                        os.remove(old_thumb)
                    except Exception:
                        pass
                ensure_thumbnail(new_path, THUMB_DIR)
            new_paths.append(new_path)

        self.set_selected_images(new_paths)
        self._reload_gallery()

    def export_selected(self) -> None:
        if not self._ensure_selection():
            return
        export_dir = "exported_images"
        os.makedirs(export_dir, exist_ok=True)
        records = self.gallery.all_records if self.gallery else load_records(self.csv_path)
        for img_path in self.selected_images:
            fname = os.path.basename(img_path)
            target_img = os.path.join(export_dir, fname)
            shutil.copy2(img_path, target_img)
            rec = next((r for r in records if r.get("file_name") == fname), None)
            if rec:
                meta_path = os.path.join(export_dir, f"{os.path.splitext(fname)[0]}.json")
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(rec, f, indent=2, ensure_ascii=False)
            ensure_thumbnail(img_path, THUMB_DIR)

        QMessageBox.information(self, "Export Complete", f"Exported {len(self.selected_images)} image(s).")

    def import_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Import")
        if not folder:
            return
        input_dir = resolve_repo_path("Input", must_exist=False, allow_absolute=False)
        os.makedirs(input_dir, exist_ok=True)

        imported = 0
        skipped = 0
        for root, _dirs, files in os.walk(folder):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext not in IMG_EXTS:
                    continue
                src = os.path.join(root, name)
                base, ext = os.path.splitext(name)
                dest = os.path.join(input_dir, name)
                if os.path.exists(dest):
                    i = 1
                    while True:
                        candidate = os.path.join(input_dir, f"{base}_{i}{ext}")
                        if not os.path.exists(candidate):
                            dest = candidate
                            break
                        i += 1
                try:
                    shutil.copy2(src, dest)
                    imported += 1
                except Exception:
                    skipped += 1

        QMessageBox.information(
            self,
            "Import Complete",
            f"Imported {imported} file(s) into Input. Skipped {skipped} file(s).",
        )

    def refresh_pipeline(self) -> None:
        try:
            repo_root = resolve_repo_path(".", must_exist=True, allow_absolute=False)
            exiftool_candidates = [
                resolve_repo_path("exiftool-13.45_64/ExifTool.exe", must_exist=False, allow_absolute=False),
                resolve_repo_path("exiftool-13.45_64/exiftool", must_exist=False, allow_absolute=False),
            ]
            exiftool_path = next((p for p in exiftool_candidates if p.exists()), None)
            exif_args = [
                sys.executable,
                "-m",
                "simage.core.exif",
                "--input",
                "Input",
                "--out",
                "out/exif_raw.jsonl",
            ]
            if exiftool_path:
                exif_args += ["--exiftool", str(exiftool_path)]
            subprocess.run(
                exif_args,
                check=True,
                cwd=str(repo_root),
            )
            subprocess.run(
                [
                    sys.executable,
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
                check=True,
                cwd=str(repo_root),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Pipeline Failed", f"Pipeline failed: {exc}")
            return

        self._reload_gallery()
        QMessageBox.information(self, "Pipeline Complete", "Records and thumbnails refreshed.")
