"""
Simage UI entrypoint.
A fast, multi-tab image pipeline UI for the Simage project.
"""

import csv
import json
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from simage.utils.paths import resolve_repo_path
from .gallery import GalleryTab
from .edit import EditTab
from .batch import BatchTab
from .settings import SettingsTab
from .viewer import ViewerTab
from .db_viewer import DatabaseViewerTab

class SimageUIMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simage Image Pipeline UI")
        self.resize(1200, 800)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.setTabsClosable(False)
        self.tabs.setMovable(True)
        gallery_tab = GalleryTab(self)
        batch_tab = BatchTab(self, gallery_tab)
        tag_tab = TagTab(self)
        edit_tab = EditTab(self)
        gallery_tab.grid.images_selected.connect(batch_tab.set_selected_images)
        gallery_tab.grid.images_selected.connect(tag_tab.set_selected_images)
        gallery_tab.grid.images_selected.connect(edit_tab.set_selected_images)
        self.tabs.addTab(gallery_tab, "Gallery & Search")
        self.tabs.addTab(tag_tab, "Tag Images")
        self.tabs.addTab(edit_tab, "Edit Images")
        self.tabs.addTab(batch_tab, "Batch Processing")
        self.tabs.addTab(SettingsTab(self, gallery_tab, batch_tab), "Settings")
        self.tabs.addTab(ViewerTab(self), "Full Image Viewer")
        self.tabs.addTab(DatabaseViewerTab(self), "DB Viewer")


# --- TagTab implementation ---
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QAbstractItemView,
    QListWidgetItem,
    QSplitter,
    QSizePolicy,
    QToolButton,
)

class TagTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.csv_path = str(resolve_repo_path("out/records.csv", must_exist=False, allow_absolute=False))
        self.custom_tags_path = str(resolve_repo_path("out/tag_list.json", must_exist=False, allow_absolute=False))
        self.records, self.fieldnames = self._load_records()
        self.record_by_name = {r.get("file_name"): r for r in self.records if r.get("file_name")}
        self.custom_tags = self._load_custom_tags()
        self.selected_files = []
        self.pending_new_tags = []
        self.pending_add_tags = []
        self.pending_edits = {}

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.info_label = QLabel("Manage tags and apply them to selected images.")
        info_row = QHBoxLayout()
        info_row.addWidget(self.info_label)
        info_row.addWidget(
            self._help_button(
                "Use this tab to create tags, rename tags, and apply tags to images."
            )
        )
        info_row.addStretch(1)
        layout.addLayout(info_row)

        top_splitter = QSplitter(Qt.Horizontal)
        bottom_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(top_splitter)
        layout.addWidget(bottom_splitter)
        layout.setStretch(0, 0)
        layout.setStretch(1, 2)
        layout.setStretch(2, 2)
        top_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        bottom_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Image list
        image_panel = QWidget()
        image_layout = QVBoxLayout(image_panel)
        image_layout.addWidget(
            self._header(
                "Image list",
                "All images from records.csv. Select images to view or edit tags.",
            )
        )
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.image_list.itemSelectionChanged.connect(self._on_image_selection_changed)
        image_layout.addWidget(self.image_list)
        top_splitter.addWidget(image_panel)

        # Current tags
        current_panel = QWidget()
        current_layout = QVBoxLayout(current_panel)
        current_layout.addWidget(
            self._header(
                "Current tags",
                "Tags currently assigned to the selected images.",
            )
        )
        self.current_tags_list = QListWidget()
        current_layout.addWidget(self.current_tags_list)
        top_splitter.addWidget(current_panel)

        # Create new tag
        new_panel = QWidget()
        new_layout = QVBoxLayout(new_panel)
        new_layout.addWidget(
            self._header(
                "Create New Tag",
                "Create new custom tags, then save them to the tag list.",
            )
        )
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("New tag name")
        new_layout.addWidget(self.new_tag_input)
        self.add_new_tag_btn = QPushButton("Add New Tag")
        self.add_new_tag_btn.clicked.connect(self._queue_new_tag)
        new_layout.addWidget(self.add_new_tag_btn)
        self.new_tags_list = QListWidget()
        new_layout.addWidget(self.new_tags_list)
        top_splitter.addWidget(new_panel)

        # Confirm save new tags
        confirm_new_panel = QWidget()
        confirm_new_layout = QVBoxLayout(confirm_new_panel)
        confirm_new_layout.addWidget(
            self._header(
                "Confirm save adding new created tags to tag List",
                "Save queued new tags into the custom tag list.",
            )
        )
        self.save_new_tags_btn = QPushButton("Save New Tags")
        self.save_new_tags_btn.clicked.connect(self._save_new_tags)
        confirm_new_layout.addWidget(self.save_new_tags_btn)
        self.custom_tags_list = QListWidget()
        confirm_new_layout.addWidget(self.custom_tags_list)
        top_splitter.addWidget(confirm_new_panel)

        # Selected images
        selected_panel = QWidget()
        selected_layout = QVBoxLayout(selected_panel)
        selected_layout.addWidget(
            self._header(
                "Selected Images",
                "Images that will receive any queued tags.",
            )
        )
        self.selected_images_list = QListWidget()
        selected_layout.addWidget(self.selected_images_list)
        bottom_splitter.addWidget(selected_panel)

        # Add tag
        add_panel = QWidget()
        add_layout = QVBoxLayout(add_panel)
        add_layout.addWidget(
            self._header(
                "Add Tag",
                "Choose tags to apply. Queue them before confirming.",
            )
        )
        self.add_tag_list = QListWidget()
        self.add_tag_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        add_layout.addWidget(self.add_tag_list)
        self.queue_add_btn = QPushButton("Queue Selected Tags")
        self.queue_add_btn.clicked.connect(self._queue_add_tags)
        add_layout.addWidget(self.queue_add_btn)
        bottom_splitter.addWidget(add_panel)

        # Added tags
        added_panel = QWidget()
        added_layout = QVBoxLayout(added_panel)
        added_layout.addWidget(
            self._header(
                "Added Tags",
                "Tags queued to apply to the selected images.",
            )
        )
        self.added_tags_list = QListWidget()
        added_layout.addWidget(self.added_tags_list)
        self.clear_added_btn = QPushButton("Clear Added Tags")
        self.clear_added_btn.clicked.connect(self._clear_added_tags)
        added_layout.addWidget(self.clear_added_btn)
        bottom_splitter.addWidget(added_panel)

        # Edit existing tag
        edit_panel = QWidget()
        edit_layout = QVBoxLayout(edit_panel)
        edit_layout.addWidget(
            self._header(
                "Edit Existing tag",
                "Rename a tag everywhere it appears.",
            )
        )
        self.edit_tag_list = QListWidget()
        self.edit_tag_list.setSelectionMode(QAbstractItemView.SingleSelection)
        edit_layout.addWidget(self.edit_tag_list)
        self.edit_tag_input = QLineEdit()
        self.edit_tag_input.setPlaceholderText("New tag name")
        edit_layout.addWidget(self.edit_tag_input)
        self.queue_edit_btn = QPushButton("Queue Tag Edit")
        self.queue_edit_btn.clicked.connect(self._queue_edit_tag)
        edit_layout.addWidget(self.queue_edit_btn)
        bottom_splitter.addWidget(edit_panel)

        # Edited tags
        edited_panel = QWidget()
        edited_layout = QVBoxLayout(edited_panel)
        edited_layout.addWidget(
            self._header(
                "Edited Tags",
                "Queued tag renames pending save.",
            )
        )
        self.edited_tags_list = QListWidget()
        edited_layout.addWidget(self.edited_tags_list)
        bottom_splitter.addWidget(edited_panel)

        # Confirm panel
        confirm_panel = QWidget()
        confirm_layout = QVBoxLayout(confirm_panel)
        confirm_layout.addWidget(
            self._header(
                "Confirm saved edited tags.",
                "Apply queued tag renames to all records.",
            )
        )
        self.save_edits_btn = QPushButton("Save Edited Tags")
        self.save_edits_btn.clicked.connect(self._apply_tag_edits)
        confirm_layout.addWidget(self.save_edits_btn)
        confirm_layout.addWidget(
            self._header(
                "Confirm adding tags to images",
                "Apply queued tags to the selected images.",
            )
        )
        self.apply_tags_btn = QPushButton("Apply Tags to Selected Images")
        self.apply_tags_btn.clicked.connect(self._apply_tags_to_selected)
        confirm_layout.addWidget(self.apply_tags_btn)
        bottom_splitter.addWidget(confirm_panel)

        top_splitter.setSizes([260, 260, 260, 260])
        bottom_splitter.setSizes([220, 220, 220, 220, 220, 220])

        self._refresh_image_list()
        self._refresh_tag_lists()

    def _help_button(self, text):
        btn = QToolButton()
        btn.setText("?")
        btn.setAutoRaise(True)
        btn.setToolTip(text)
        btn.setCursor(Qt.WhatsThisCursor)
        btn.setFixedSize(16, 16)
        return btn

    def _header(self, title, tip):
        row = QHBoxLayout()
        row.addWidget(QLabel(title))
        row.addWidget(self._help_button(tip))
        row.addStretch(1)
        widget = QWidget()
        widget.setLayout(row)
        return widget

    def _load_records(self):
        if not os.path.exists(self.csv_path):
            return [], []
        with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            return rows, reader.fieldnames or []

    def _save_records(self):
        if not self.fieldnames:
            fieldnames = sorted({k for r in self.records for k in r.keys()})
        else:
            fieldnames = list(self.fieldnames)
        backup_path = self.csv_path + ".bak"
        if os.path.exists(self.csv_path):
            if not os.path.exists(backup_path):
                os.replace(self.csv_path, backup_path)
            else:
                os.remove(self.csv_path)
                os.replace(backup_path, self.csv_path)
                os.replace(self.csv_path, backup_path)
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.records:
                writer.writerow(row)

    def _load_custom_tags(self):
        if not os.path.exists(self.custom_tags_path):
            return set()
        try:
            with open(self.custom_tags_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return set(str(t).strip() for t in data if str(t).strip())
        except Exception:
            return set()
        return set()

    def _save_custom_tags(self):
        os.makedirs(os.path.dirname(self.custom_tags_path), exist_ok=True)
        with open(self.custom_tags_path, "w", encoding="utf-8") as f:
            json.dump(sorted(self.custom_tags), f, indent=2, ensure_ascii=False)

    def _split_tags(self, text):
        if not text:
            return []
        s = str(text).replace("\n", ",")
        parts = [p.strip() for p in s.split(",")]
        return [p for p in parts if p]

    def _dedupe_tags(self, tags):
        seen = set()
        out = []
        for t in tags:
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
        return out

    def _collect_tag_map(self):
        tag_map = {}
        for rec in self.records:
            prompt = rec.get("prompt", "")
            for tag in self._split_tags(prompt):
                key = tag.lower()
                if key not in tag_map:
                    tag_map[key] = tag
        for tag in self.custom_tags:
            key = tag.lower()
            if key not in tag_map:
                tag_map[key] = tag
        return tag_map

    def _refresh_image_list(self):
        self.image_list.blockSignals(True)
        self.image_list.clear()
        names = sorted(self.record_by_name.keys())
        for name in names:
            self.image_list.addItem(name)
        self.image_list.blockSignals(False)

    def _refresh_tag_lists(self):
        tag_map = self._collect_tag_map()
        all_tags = [tag_map[k] for k in sorted(tag_map.keys())]

        self.add_tag_list.clear()
        self.edit_tag_list.clear()
        for tag in all_tags:
            self.add_tag_list.addItem(tag)
            self.edit_tag_list.addItem(tag)

        self.custom_tags_list.clear()
        for tag in sorted(self.custom_tags):
            self.custom_tags_list.addItem(tag)

        self._refresh_current_tags()
        self._refresh_pending_lists()

    def _refresh_current_tags(self):
        tags = []
        for name in self.selected_files:
            rec = self.record_by_name.get(name)
            if not rec:
                continue
            tags.extend(self._split_tags(rec.get("prompt", "")))
        tags = sorted(self._dedupe_tags(tags), key=str.lower)
        self.current_tags_list.clear()
        for tag in tags:
            self.current_tags_list.addItem(tag)

    def _refresh_pending_lists(self):
        self.new_tags_list.clear()
        for tag in self.pending_new_tags:
            self.new_tags_list.addItem(tag)

        self.added_tags_list.clear()
        for tag in self.pending_add_tags:
            self.added_tags_list.addItem(tag)

        self.edited_tags_list.clear()
        for old_key, (old_tag, new_tag) in self.pending_edits.items():
            self.edited_tags_list.addItem(f"{old_tag} -> {new_tag}")

        self.selected_images_list.clear()
        for name in self.selected_files:
            self.selected_images_list.addItem(name)

    def _on_image_selection_changed(self):
        selected = [i.text() for i in self.image_list.selectedItems()]
        self.selected_files = selected
        self._refresh_current_tags()
        self._refresh_pending_lists()

    def set_selected_images(self, image_paths):
        names = [os.path.basename(p) for p in image_paths if p]
        self.selected_files = [n for n in names if n in self.record_by_name]
        self.image_list.blockSignals(True)
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            item.setSelected(item.text() in self.selected_files)
        self.image_list.blockSignals(False)
        self._refresh_current_tags()
        self._refresh_pending_lists()

    def _queue_new_tag(self):
        tag = self.new_tag_input.text().strip()
        if not tag:
            return
        if tag not in self.pending_new_tags:
            self.pending_new_tags.append(tag)
        self.new_tag_input.clear()
        self._refresh_pending_lists()

    def _save_new_tags(self):
        if not self.pending_new_tags:
            QMessageBox.information(self, "No New Tags", "Add new tags before saving.")
            return
        for tag in self.pending_new_tags:
            self.custom_tags.add(tag)
        self.pending_new_tags = []
        self._save_custom_tags()
        self._refresh_tag_lists()

    def _queue_add_tags(self):
        selected = [i.text() for i in self.add_tag_list.selectedItems()]
        if not selected:
            return
        for tag in selected:
            if tag not in self.pending_add_tags:
                self.pending_add_tags.append(tag)
        self._refresh_pending_lists()

    def _clear_added_tags(self):
        self.pending_add_tags = []
        self._refresh_pending_lists()

    def _queue_edit_tag(self):
        selected_items = self.edit_tag_list.selectedItems()
        if not selected_items:
            return
        old_tag = selected_items[0].text()
        new_tag = self.edit_tag_input.text().strip()
        if not new_tag:
            return
        self.pending_edits[old_tag.lower()] = (old_tag, new_tag)
        self.edit_tag_input.clear()
        self._refresh_pending_lists()

    def _apply_tag_edits(self):
        if not self.pending_edits:
            QMessageBox.information(self, "No Edits", "Queue tag edits before saving.")
            return
        for rec in self.records:
            prompt = rec.get("prompt", "")
            tags = self._split_tags(prompt)
            updated = []
            for tag in tags:
                key = tag.lower()
                if key in self.pending_edits:
                    updated.append(self.pending_edits[key][1])
                else:
                    updated.append(tag)
            rec["prompt"] = ", ".join(self._dedupe_tags(updated))

        updated_custom = set()
        for tag in self.custom_tags:
            key = tag.lower()
            if key in self.pending_edits:
                updated_custom.add(self.pending_edits[key][1])
            else:
                updated_custom.add(tag)
        self.custom_tags = updated_custom

        self._save_records()
        self._save_custom_tags()
        self.pending_edits = {}
        self.records, self.fieldnames = self._load_records()
        self.record_by_name = {r.get("file_name"): r for r in self.records if r.get("file_name")}
        self._refresh_tag_lists()

    def _apply_tags_to_selected(self):
        if not self.selected_files or not self.pending_add_tags:
            QMessageBox.information(self, "Nothing to Apply", "Select images and queue tags to apply.")
            return
        selected_set = set(self.selected_files)
        for rec in self.records:
            if rec.get("file_name") not in selected_set:
                continue
            tags = self._split_tags(rec.get("prompt", ""))
            tags.extend(self.pending_add_tags)
            rec["prompt"] = ", ".join(self._dedupe_tags(tags))
        self._save_records()
        self.pending_add_tags = []
        self.records, self.fieldnames = self._load_records()
        self.record_by_name = {r.get("file_name"): r for r in self.records if r.get("file_name")}
        self._refresh_tag_lists()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SimageUIMain()
    win.show()
    sys.exit(app.exec())
