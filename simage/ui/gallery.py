"""
Gallery/search tab for Simage UI.
Fast, scrollable, async thumbnail grid for large image sets.
"""

import os

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
)
from PySide6.QtCore import Qt

from simage.utils.paths import resolve_repo_path
from .thumb_grid import ThumbnailGrid
from .record_filter import load_records, filter_records, filter_by_tags
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
        self.update_grid()
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
        import json
        import shutil
        from .thumbnails import ensure_thumbnail, THUMB_DIR
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
        # Show only filtered images in the grid
        file_names = [rec["file_name"] for rec in self.filtered_records if "file_name" in rec]
        # Patch: ThumbnailGrid expects folder, but we can set thumbs directly for now
        self.grid.thumbs = [os.path.join(self.grid.folder, f) for f in file_names]
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
