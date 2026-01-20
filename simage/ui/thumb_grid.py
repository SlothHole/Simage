"""
Fast, virtualized thumbnail grid widget for SimageUI.
"""


from PySide6.QtWidgets import QWidget, QScrollArea, QGridLayout, QLabel, QSizePolicy, QVBoxLayout
from PySide6.QtCore import Qt, QSize, Signal, QRect, QEvent
from PySide6.QtGui import QPixmap
import os
from .scanner import ensure_thumbnails_for_folder



class ThumbnailGrid(QWidget):
    image_selected = Signal(str, str)  # (image_path, thumb_path)
    images_selected = Signal(list)  # List of selected image paths

    THUMB_SIZE = 128
    COLS = 8
    PADDING = 4

    def __init__(self, parent=None, folder=None):
        super().__init__(parent)
        self.folder = folder or os.getcwd()
        self.thumbs = ensure_thumbnails_for_folder(self.folder)
        self.selected_indices = set()

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.grid = QGridLayout(self.inner)
        self.grid.setSpacing(self.PADDING)
        self.grid.setContentsMargins(0,0,0,0)
        self.inner.setLayout(self.grid)
        self.scroll.setWidget(self.inner)

        layout = QVBoxLayout(self)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

        self.visible_labels = {}
        self.scroll.verticalScrollBar().valueChanged.connect(self.update_visible_thumbnails)
        self.inner.installEventFilter(self)
        self.update_grid_geometry()
        self.update_visible_thumbnails()

    def clear_selection(self):
        self.selected_indices.clear()
        self.update_visible_thumbnails()
        self.images_selected.emit([])

    def get_selected_images(self):
        return [self.thumbs[i] for i in self.selected_indices if 0 <= i < len(self.thumbs)]

    def update_grid_geometry(self):
        rows = (len(self.thumbs) + self.COLS - 1) // self.COLS
        for i in range(rows):
            for j in range(self.COLS):
                idx = i * self.COLS + j
                if idx >= len(self.thumbs):
                    break
                # Placeholders only; actual QLabel created in update_visible_thumbnails
                self.grid.addWidget(QWidget(), i, j)
        self.inner.setMinimumHeight(rows * (self.THUMB_SIZE + self.PADDING))

    def update_visible_thumbnails(self):
        area = self.scroll.viewport().rect()
        y0 = self.scroll.verticalScrollBar().value()
        y1 = y0 + area.height()
        thumb_h = self.THUMB_SIZE + self.PADDING
        first_row = max(0, y0 // thumb_h - 2)
        last_row = min((len(self.thumbs) + self.COLS - 1) // self.COLS, (y1 // thumb_h) + 2)
        # Remove labels not in visible range
        to_remove = [k for k in self.visible_labels if not (first_row <= k[0] < last_row)]
        for k in to_remove:
            label = self.visible_labels.pop(k)
            self.grid.removeWidget(label)
            label.deleteLater()
        # Add visible labels
        for row in range(first_row, last_row):
            for col in range(self.COLS):
                idx = row * self.COLS + col
                if idx >= len(self.thumbs):
                    break
                key = (row, col)
                if key not in self.visible_labels:
                    thumb_path = self.thumbs[idx]
                    label = QLabel()
                    label.setFixedSize(self.THUMB_SIZE, self.THUMB_SIZE)
                    label.setStyleSheet("background: #222; border: 1px solid #888;")
                    label.setAlignment(Qt.AlignCenter)
                    if os.path.exists(thumb_path):
                        pix = QPixmap(thumb_path)
                        label.setPixmap(pix.scaled(self.THUMB_SIZE, self.THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    else:
                        label.setText("?")
                    if idx in self.selected_indices:
                        label.setStyleSheet("background: #444; border: 2px solid #00f;")
                    label.mousePressEvent = self._make_select_handler(idx)
                    self.grid.addWidget(label, row, col)
                    self.visible_labels[key] = label

    def eventFilter(self, obj, event):
        if obj is self.inner and event.type() == QEvent.Resize:
            self.update_visible_thumbnails()
        return super().eventFilter(obj, event)

    def _make_select_handler(self, idx):
        def handler(event):
            if 0 <= idx < len(self.thumbs):
                if event.modifiers() & Qt.ControlModifier:
                    # Toggle selection
                    if idx in self.selected_indices:
                        self.selected_indices.remove(idx)
                    else:
                        self.selected_indices.add(idx)
                    self.update_visible_thumbnails()
                    self.images_selected.emit(self.get_selected_images())
                else:
                    self.selected_indices = {idx}
                    self.update_visible_thumbnails()
                    img_path = self.thumbs[idx].replace('.thumbnails', '').replace('\\', os.sep).replace('/', os.sep)
                    self.image_selected.emit(img_path, self.thumbs[idx])
                    self.images_selected.emit(self.get_selected_images())
        return handler

    def sizeHint(self):
        return QSize(1024, 600)
