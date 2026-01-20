"""
Simage UI entrypoint.
A fast, multi-tab image pipeline UI for the Simage project.
"""

import os
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from simage.utils.paths import resolve_repo_path
from .gallery import GalleryTab
from .edit import EditTab
from .batch import BatchTab
from .settings import SettingsTab
from .viewer import ViewerTab

class SimageUIMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simage Image Pipeline UI")
        self.resize(1200, 800)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.setTabsClosable(False)
        self.tabs.setMovable(True)
        self.tabs.addTab(GalleryTab(self), "Gallery & Search")
        self.tabs.addTab(TagTab(self), "Tag Images")
        self.tabs.addTab(EditTab(self), "Edit Images")
        self.tabs.addTab(BatchTab(self), "Batch Processing")
        self.tabs.addTab(SettingsTab(self), "Settings")
        self.tabs.addTab(ViewerTab(self), "Full Image Viewer")


# --- TagTab implementation ---
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QListWidget,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
)
from .csv_edit import amend_records_csv
from .change_log import ChangeLogger


class TagTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags = {}  # {image_path: [tags]}
        self.renames = {}  # {old_path: new_path}
        self.csv_path = str(resolve_repo_path("out/records.csv", must_exist=False, allow_absolute=False))
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.info_label = QLabel("Select images from the gallery and add tags. Tags and renames are persisted to records.csv (with backup).")
        layout.addWidget(self.info_label)

        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.selected_list)

        tag_input_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter tags, comma-separated")
        tag_input_layout.addWidget(self.tag_input)
        self.apply_btn = QPushButton("Apply Tags")
        self.apply_btn.clicked.connect(self.apply_tags)
        tag_input_layout.addWidget(self.apply_btn)
        layout.addLayout(tag_input_layout)

        rename_layout = QHBoxLayout()
        self.rename_input = QLineEdit()
        self.rename_input.setPlaceholderText("Rename selected image (new filename)")
        rename_layout.addWidget(self.rename_input)
        self.rename_btn = QPushButton("Rename Image")
        self.rename_btn.clicked.connect(self.rename_image)
        rename_layout.addWidget(self.rename_btn)
        layout.addLayout(rename_layout)

        self.tag_display = QTextEdit()
        self.tag_display.setReadOnly(True)
        layout.addWidget(self.tag_display)

        # On startup, check for unsaved changes
        self.recover_unsaved_changes()

    def recover_unsaved_changes(self):
        changes = ChangeLogger.load_changes()
        if changes:
            from PySide6.QtWidgets import QMessageBox
            if QMessageBox.question(self, "Recover Unsaved Changes", "Unsaved changes were found. Apply them?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                for change in changes:
                    if change.get("type") == "tag":
                        self.tags.setdefault(change["img"], []).extend(change["tags"])
                ChangeLogger.clear()
                self.update_tag_display()

    def set_selected_images(self, image_paths):
        self.selected_list.clear()
        for path in image_paths:
            display_path = self.renames.get(path, path)
            self.selected_list.addItem(display_path)

    def apply_tags(self):
        selected = [self.selected_list.item(i).text() for i in range(self.selected_list.count()) if self.selected_list.item(i).isSelected()]
        tags = [t.strip() for t in self.tag_input.text().split(",") if t.strip()]
        if not selected or not tags:
            QMessageBox.warning(self, "No Selection", "Select images and enter at least one tag.")
            return
        for img in selected:
            self.tags.setdefault(img, []).extend([t for t in tags if t not in self.tags.get(img, [])])
            # Log unsaved change
            ChangeLogger.log_change({"type": "tag", "img": img, "tags": tags})
        # Persist tag changes to records.csv
        updates = [{"file_name": img, "prompt": ", ".join(self.tags[img])} for img in selected]
        amend_records_csv(self.csv_path, updates, key_field="file_name")
        ChangeLogger.clear()
        self.update_tag_display()

    def rename_image(self):
        selected = [self.selected_list.item(i).text() for i in range(self.selected_list.count()) if self.selected_list.item(i).isSelected()]
        new_name = self.rename_input.text().strip()
        if len(selected) != 1 or not new_name:
            QMessageBox.warning(self, "Rename Error", "Select exactly one image and enter a new filename.")
            return
        old_path = selected[0]
        all_paths = set(self.renames.values()) | set(self.renames.keys())
        if new_name in all_paths:
            base, ext = os.path.splitext(new_name)
            i = 1
            candidate = f"{base}_{i}{ext}"
            while candidate in all_paths:
                i += 1
                candidate = f"{base}_{i}{ext}"
            new_name = candidate
        self.renames[old_path] = new_name
        if old_path in self.tags:
            self.tags[new_name] = self.tags.pop(old_path)
        # Persist rename to records.csv
        updates = [{"file_name": old_path, "file_name": new_name}]
        amend_records_csv(self.csv_path, updates, key_field="file_name")
        self.set_selected_images(list(all_paths))
        self.update_tag_display()

    def update_tag_display(self):
        lines = [f"{img}: {', '.join(tags)}" for img, tags in self.tags.items()]
        self.tag_display.setPlainText("\n".join(lines))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SimageUIMain()
    win.show()
    sys.exit(app.exec())
