"""
Gallery/search tab for Simage UI.
Fast, scrollable, async thumbnail grid for large image sets.
"""

import csv
import json
import os
import sqlite3
import sys

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSplitter,
    QSizePolicy,
    QTextEdit,
    QFrame,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt

from simage.utils.paths import resolve_repo_path
from .thumb_grid import ThumbnailGrid
from .record_filter import load_records, filter_records, filter_by_tags
from .scanner import IMG_EXTS
from .thumbnails import THUMB_DIR, ensure_thumbnail, thumbnail_path_for_source

CSV_COLUMNS = [
    "id",
    "source_file",
    "file_name",
    "ext",
    "width",
    "height",
    "format_hint",
    "model",
    "sampler",
    "scheduler",
    "steps",
    "cfg_scale",
    "seed",
    "prompt",
    "negative_prompt",
]
class GalleryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # Left: Search/filter/sort + Thumbnail grid + batch controls + export
        grid_widget = QWidget()
        grid_layout = QVBoxLayout(grid_widget)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by filename, metadata...")
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.apply_search)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)

        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Filter by tags (comma-separated)")
        self.tag_btn = QPushButton("Filter Tags")
        self.tag_btn.clicked.connect(self.apply_tag_filter)
        search_layout.addWidget(self.tag_input)
        search_layout.addWidget(self.tag_btn)

        self.sort_input = QLineEdit()
        self.sort_input.setPlaceholderText("Sort by: file_name, date, tag_count...")
        self.sort_btn = QPushButton("Sort")
        self.sort_btn.clicked.connect(self.apply_sort)
        search_layout.addWidget(self.sort_input)
        search_layout.addWidget(self.sort_btn)

        grid_layout.addLayout(search_layout)

        # Batch operation controls
        batch_layout = QHBoxLayout()
        self.batch_tag_input = QLineEdit()
        self.batch_tag_input.setPlaceholderText("Batch tag: tags, comma-separated")
        self.batch_tag_btn = QPushButton("Apply Batch Tags")
        self.batch_tag_btn.clicked.connect(self.apply_batch_tags)
        batch_layout.addWidget(self.batch_tag_input)
        batch_layout.addWidget(self.batch_tag_btn)

        self.batch_rename_input = QLineEdit()
        self.batch_rename_input.setPlaceholderText("Batch rename: base name")
        self.batch_rename_btn = QPushButton("Batch Rename")
        self.batch_rename_btn.clicked.connect(self.apply_batch_rename)
        batch_layout.addWidget(self.batch_rename_input)
        batch_layout.addWidget(self.batch_rename_btn)

        self.batch_move_input = QLineEdit()
        self.batch_move_input.setPlaceholderText("Batch move: target folder")
        self.batch_move_btn = QPushButton("Batch Move")
        self.batch_move_btn.clicked.connect(self.apply_batch_move)
        batch_layout.addWidget(self.batch_move_input)
        batch_layout.addWidget(self.batch_move_btn)

        self.export_btn = QPushButton("Export Selected")
        self.export_btn.clicked.connect(self.export_selected)
        batch_layout.addWidget(self.export_btn)

        self.import_btn = QPushButton("Import Folder")
        self.import_btn.clicked.connect(self.import_folder)
        batch_layout.addWidget(self.import_btn)

        self.refresh_btn = QPushButton("Refresh Pipeline")
        self.refresh_btn.clicked.connect(self.refresh_pipeline)
        batch_layout.addWidget(self.refresh_btn)

        grid_layout.addLayout(batch_layout)

        self.grid = ThumbnailGrid()
        self.grid.image_selected.connect(self.on_image_selected)
        self.grid.images_selected.connect(self.on_images_selected)
        grid_layout.addWidget(self.grid)

        splitter.addWidget(grid_widget)

        # Right: Side panel (image preview + info)
        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        self.image_preview = QLabel("No image selected")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumSize(256, 256)
        self.image_preview.setFrameShape(QFrame.Box)
        self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        side_layout.addWidget(self.image_preview)

        self.info_window = QTextEdit()
        self.info_window.setReadOnly(True)
        self.info_window.setMinimumHeight(120)
        side_layout.addWidget(self.info_window)
        side_panel.setLayout(side_layout)
        splitter.addWidget(side_panel)

        splitter.setSizes([900, 300])
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # Load all records for filtering
        self.csv_path = str(resolve_repo_path("out/records.csv", must_exist=False, allow_absolute=False))
        self.all_records = load_records(self.csv_path)
        self.filtered_records = self.all_records
        self.selected_images = []
        self.csv_columns = self._compute_csv_columns(self.all_records)
        self.thumb_cache = {}
        self.update_grid()

    def _compute_csv_columns(self, records):
        extra = sorted({k for r in records for k in r.keys()} - set(CSV_COLUMNS))
        return CSV_COLUMNS + extra

    def _record_key(self, rec):
        return rec.get("source_file") or rec.get("file_name") or ""

    def _record_image_path(self, rec):
        src = rec.get("source_file")
        if isinstance(src, str) and src:
            if os.path.isabs(src):
                return src
            return str(resolve_repo_path(src, must_exist=False, allow_absolute=False))
        name = rec.get("file_name")
        if isinstance(name, str) and name:
            return str(resolve_repo_path(os.path.join("Input", name), must_exist=False, allow_absolute=False))
        return ""

    def _thumbnail_path_for_record(self, rec):
        img_path = self._record_image_path(rec)
        if not img_path:
            return ""
        return thumbnail_path_for_source(img_path, THUMB_DIR)

    def _thumb_for_record(self, rec):
        key = self._record_key(rec)
        if key in self.thumb_cache:
            return self.thumb_cache[key]
        img_path = self._record_image_path(rec)
        if img_path and os.path.exists(img_path):
            thumb = ensure_thumbnail(img_path, THUMB_DIR)
        else:
            thumb = self._thumbnail_path_for_record(rec)
            if not os.path.exists(thumb):
                thumb = ""
        self.thumb_cache[key] = thumb
        return thumb

    def _load_jsonl(self, path):
        if not os.path.exists(path):
            return []
        out = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out

    def _write_jsonl(self, path, records):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _write_csv(self, path, records):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.csv_columns)
            w.writeheader()
            for rec in records:
                row = {c: rec.get(c) for c in self.csv_columns}
                w.writerow(row)

    def _delete_missing_records(self, records):
        for rec in records:
            thumb = self._thumbnail_path_for_record(rec)
            if thumb and os.path.exists(thumb):
                try:
                    os.remove(thumb)
                except Exception:
                    pass

        db_path = resolve_repo_path("out/images.db", must_exist=False, allow_absolute=False)
        if not db_path.exists():
            return
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA foreign_keys=ON;")
            for rec in records:
                src = rec.get("source_file")
                if src:
                    conn.execute("DELETE FROM images WHERE source_file = ?", (src,))
                else:
                    rec_id = rec.get("id")
                    if rec_id:
                        conn.execute("DELETE FROM images WHERE id = ?", (rec_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _merge_missing_values(self, target, source):
        for k, v in source.items():
            if k in target and isinstance(target[k], dict) and isinstance(v, dict):
                self._merge_missing_values(target[k], v)
            elif k not in target or target[k] in (None, ""):
                target[k] = v

    def _merge_records(self, new_records, old_records):
        old_by_key = {self._record_key(r): r for r in old_records if self._record_key(r)}
        old_by_name = {}
        for r in old_records:
            name = r.get("file_name")
            if name and name not in old_by_name:
                old_by_name[name] = r

        for rec in new_records:
            key = self._record_key(rec)
            old = old_by_key.get(key) or old_by_name.get(rec.get("file_name"))
            if not old:
                continue
            for col in self.csv_columns:
                if rec.get(col) in (None, "") and old.get(col) not in (None, ""):
                    rec[col] = old.get(col)
    def apply_sort(self):
        key = self.sort_input.text().strip()
        if not key:
            return
        def tag_count(rec):
            return len([t for t in rec.get("prompt", "").split(",") if t.strip()])
        if key == "tag_count":
            self.filtered_records = sorted(self.filtered_records, key=tag_count, reverse=True)
        else:
            self.filtered_records = sorted(self.filtered_records, key=lambda r: r.get(key, ""))
        self.update_grid()

    def export_selected(self):
        import shutil
        if not self.selected_images:
            return
        export_dir = "exported_images"
        os.makedirs(export_dir, exist_ok=True)
        for img_path in self.selected_images:
            fname = os.path.basename(img_path)
            # Copy image
            target_img = os.path.join(export_dir, fname)
            shutil.copy2(img_path, target_img)
            # Export metadata as sidecar JSON
            rec = next((r for r in self.all_records if r.get("file_name") == fname), None)
            if rec:
                meta_path = os.path.join(export_dir, f"{os.path.splitext(fname)[0]}.json")
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(rec, f, indent=2)
            # Ensure thumbnail remains in .thumbnails (archive)
            ensure_thumbnail(img_path, THUMB_DIR)

    def import_folder(self):
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
                    import shutil
                    shutil.copy2(src, dest)
                    imported += 1
                except Exception:
                    skipped += 1

        QMessageBox.information(
            self,
            "Import Complete",
            f"Imported {imported} file(s) into Input. Skipped {skipped} file(s).",
        )

    def refresh_pipeline(self):
        old_records = load_records(self.csv_path)
        old_jsonl_path = str(resolve_repo_path("out/records.jsonl", must_exist=False, allow_absolute=False))
        old_jsonl = self._load_jsonl(old_jsonl_path)
        try:
            import subprocess
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

        new_records = load_records(self.csv_path)
        new_jsonl_path = str(resolve_repo_path("out/records.jsonl", must_exist=False, allow_absolute=False))
        new_jsonl = self._load_jsonl(new_jsonl_path)

        self.csv_columns = self._compute_csv_columns(old_records + new_records)
        self._merge_records(new_records, old_records)

        old_jsonl_by_key = {self._record_key(r): r for r in old_jsonl if self._record_key(r)}
        old_jsonl_by_name = {}
        for r in old_jsonl:
            name = r.get("file_name")
            if name and name not in old_jsonl_by_name:
                old_jsonl_by_name[name] = r
        for rec in new_jsonl:
            key = self._record_key(rec)
            old = old_jsonl_by_key.get(key) or old_jsonl_by_name.get(rec.get("file_name"))
            if old:
                self._merge_missing_values(rec, old)

        self._write_csv(self.csv_path, new_records)
        self._write_jsonl(new_jsonl_path, new_jsonl)

        old_map = {self._record_key(r): r for r in old_records if self._record_key(r)}
        new_keys = {self._record_key(r) for r in new_records if self._record_key(r)}
        missing_records = [old_map[k] for k in old_map if k not in new_keys]

        if missing_records:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Missing Images")
            msg.setText(f"{len(missing_records)} image(s) are missing from Input.")
            msg.setInformativeText("Delete their info + thumbnails, or keep them for reimport later?")
            delete_btn = msg.addButton("Delete", QMessageBox.DestructiveRole)
            keep_btn = msg.addButton("Keep for Later", QMessageBox.AcceptRole)
            msg.setDefaultButton(keep_btn)
            msg.exec()

            if msg.clickedButton() == delete_btn:
                self._delete_missing_records(missing_records)
            else:
                merged_records = list(new_records)
                merged_records.extend(missing_records)
                self.csv_columns = self._compute_csv_columns(merged_records)
                self._write_csv(self.csv_path, merged_records)

                old_jsonl_map = {self._record_key(r): r for r in old_jsonl if self._record_key(r)}
                merged_jsonl = list(new_jsonl)
                for rec in missing_records:
                    key = self._record_key(rec)
                    merged_jsonl.append(old_jsonl_map.get(key, rec))
                self._write_jsonl(new_jsonl_path, merged_jsonl)

                new_records = load_records(self.csv_path)

        self.all_records = new_records
        self.filtered_records = self.all_records
        self.thumb_cache = {}
        self.update_grid()
        QMessageBox.information(self, "Pipeline Complete", "Records and thumbnails refreshed.")

    def on_images_selected(self, image_paths):
        self.selected_images = image_paths

    def apply_batch_tags(self):
        tags = [t.strip() for t in self.batch_tag_input.text().split(",") if t.strip()]
        if not self.selected_images or not tags:
            return
        from .csv_edit import amend_records_csv
        updates = []
        for img_path in self.selected_images:
            fname = os.path.basename(img_path)
            rec = next((r for r in self.all_records if r.get("file_name") == fname), None)
            if rec:
                prompt = rec.get("prompt", "")
                prompt_tags = set([t.strip() for t in prompt.split(",") if t.strip()])
                prompt_tags.update(tags)
                updates.append({"file_name": fname, "prompt": ", ".join(sorted(prompt_tags))})
        amend_records_csv(self.csv_path, updates, key_field="file_name")
        self.all_records = load_records(self.csv_path)
        self.filtered_records = self.all_records
        self.update_grid()

    def apply_batch_rename(self):
        base = self.batch_rename_input.text().strip()
        if not self.selected_images or not base:
            return
        from .csv_edit import amend_records_csv
        from .thumbnails import ensure_thumbnail, THUMB_DIR
        updates = []
        for i, img_path in enumerate(self.selected_images):
            fname = os.path.basename(img_path)
            ext = os.path.splitext(fname)[1]
            new_name = f"{base}_{i+1}{ext}"
            new_path = os.path.join(os.path.dirname(img_path), new_name)
            # Rename image file
            if os.path.exists(img_path):
                os.rename(img_path, new_path)
            # Rename/move thumbnail
            thumb_dir = os.path.join(os.path.dirname(img_path), THUMB_DIR)
            old_thumb = os.path.join(thumb_dir, fname)
            new_thumb = os.path.join(thumb_dir, new_name)
            if os.path.exists(old_thumb):
                os.rename(old_thumb, new_thumb)
            else:
                ensure_thumbnail(new_path, thumb_dir)
            updates.append({"file_name": fname, "file_name": new_name})
        amend_records_csv(self.csv_path, updates, key_field="file_name")
        self.all_records = load_records(self.csv_path)
        self.filtered_records = self.all_records
        self.update_grid()

    def apply_batch_move(self):
        target = self.batch_move_input.text().strip()
        if not self.selected_images or not target:
            return
        from .thumbnails import ensure_thumbnail, THUMB_DIR
        os.makedirs(target, exist_ok=True)
        for img_path in self.selected_images:
            fname = os.path.basename(img_path)
            new_path = os.path.join(target, fname)
            # Move image file
            if os.path.exists(img_path) and not os.path.exists(new_path):
                os.rename(img_path, new_path)
            # Move thumbnail
            old_thumb_dir = os.path.join(os.path.dirname(img_path), THUMB_DIR)
            new_thumb_dir = os.path.join(target, THUMB_DIR)
            os.makedirs(new_thumb_dir, exist_ok=True)
            old_thumb = os.path.join(old_thumb_dir, fname)
            new_thumb = os.path.join(new_thumb_dir, fname)
            if os.path.exists(old_thumb):
                os.rename(old_thumb, new_thumb)
            else:
                ensure_thumbnail(new_path, new_thumb_dir)
        self.update_grid()

    def update_grid(self):
        thumbs = []
        images = []
        for rec in self.filtered_records:
            img_path = self._record_image_path(rec)
            if not img_path:
                continue
            thumb_path = self._thumb_for_record(rec)
            thumbs.append(thumb_path)
            images.append(img_path)
        self.grid.thumbs = thumbs
        self.grid.image_paths = images
        self.grid.update_grid_geometry()
        self.grid.update_visible_thumbnails()

    def apply_search(self):
        query = self.search_input.text().strip()
        self.filtered_records = filter_records(self.all_records, query)
        self.update_grid()

    def apply_tag_filter(self):
        tags = [t.strip() for t in self.tag_input.text().split(",") if t.strip()]
        self.filtered_records = filter_by_tags(self.all_records, tags)
        self.update_grid()

    def on_image_selected(self, img_path, thumb_path):
        from PySide6.QtGui import QPixmap
        import os
        # Show preview
        if os.path.exists(img_path):
            pix = QPixmap(img_path)
            self.image_preview.setPixmap(pix.scaled(
                self.image_preview.width(),
                self.image_preview.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation))
            self.image_preview.setText("")
        else:
            self.image_preview.setPixmap(QPixmap())
            self.image_preview.setText("Image not found")
        # Show info (with metadata)
        rec = next((r for r in self.all_records if r.get("file_name") == os.path.basename(img_path)), None)
        if rec:
            info = "\n".join(f"{k}: {v}" for k, v in rec.items())
        else:
            info = f"Image Path: {img_path}\nThumbnail Path: {thumb_path}"
        self.info_window.setPlainText(info)
