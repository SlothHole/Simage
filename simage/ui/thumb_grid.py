"""
Fast, virtualized thumbnail grid widget for Simage UI.
"""


from PySide6.QtWidgets import QWidget, QScrollArea, QGridLayout, QLabel, QSizePolicy, QVBoxLayout
from PySide6.QtCore import Qt, QSize, Signal, QEvent
from PySide6.QtGui import QPixmap
import os
from collections import deque



class ThumbnailGrid(QWidget):
    image_selected = Signal(str, str)  # (image_path, thumb_path)
    images_selected = Signal(list)  # List of selected image paths

    THUMB_SIZE = 128
    COL_SPACING = 4
    ROW_SPACING = 2

    def __init__(self, parent=None, folder=None):
        super().__init__(parent)
        self.folder = folder or os.getcwd()
        self.thumbs = []
        self.image_paths = []
        self.selected_indices = set()
        self._pixmap_cache = {}
        self._pixmap_cache_order = deque()
        self._pixmap_cache_max = 256
        self._cols = 1
        self._row_count = 0
        self._col_count = 0

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.inner = QWidget()
        self.inner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.grid = QGridLayout(self.inner)
        self.grid.setHorizontalSpacing(self.COL_SPACING)
        self.grid.setVerticalSpacing(self.ROW_SPACING)
        self.grid.setContentsMargins(0,0,0,0)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.inner.setLayout(self.grid)
        self.scroll.setWidget(self.inner)

        layout = QVBoxLayout(self)
        layout.addWidget(self.scroll)
        self.setLayout(layout)
        self.setFocusPolicy(Qt.StrongFocus)

        self.visible_labels = {}
        self.scroll.verticalScrollBar().valueChanged.connect(self.update_visible_thumbnails)
        self.inner.installEventFilter(self)
        self.scroll.viewport().installEventFilter(self)
        self.update_grid_geometry()
        self.update_visible_thumbnails()

    def clear_selection(self):
        self.selected_indices.clear()
        self.update_visible_thumbnails()
        self.images_selected.emit([])

    def _first_selected_index(self) -> int:
        if not self.selected_indices:
            return -1
        return sorted(self.selected_indices)[0]

    def _ensure_visible(self, idx: int):
        if idx < 0:
            return
        row = idx // max(1, self._cols)
        y = row * (self.THUMB_SIZE + self.ROW_SPACING)
        bar = self.scroll.verticalScrollBar()
        view_h = self.scroll.viewport().height()
        if y < bar.value():
            bar.setValue(y)
        elif y + self.THUMB_SIZE > bar.value() + view_h:
            bar.setValue(max(0, y - view_h + self.THUMB_SIZE))

    def get_selected_images(self):
        out = []
        for i in self.selected_indices:
            if 0 <= i < len(self.thumbs):
                out.append(self._image_path_for_index(i))
        return out

    def _image_path_for_index(self, idx: int) -> str:
        if self.image_paths and idx < len(self.image_paths):
            return self.image_paths[idx]
        if 0 <= idx < len(self.thumbs):
            return self.thumbs[idx].replace(".thumbnails", "").replace("\\", os.sep).replace("/", os.sep)
        return ""

    def _compute_cols(self) -> int:
        width = self.scroll.viewport().width()
        cell = self.THUMB_SIZE + self.COL_SPACING
        if width <= 0:
            return 1
        return max(1, (width + self.COL_SPACING) // cell)

    def update_grid_geometry(self):
        for label in self.visible_labels.values():
            self.grid.removeWidget(label)
            label.deleteLater()
        self.visible_labels.clear()

        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        prev_rows = self._row_count
        prev_cols = self._col_count
        self._cols = self._compute_cols()
        rows = (len(self.thumbs) + self._cols - 1) // self._cols
        self._row_count = rows
        self._col_count = self._cols

        for r in range(rows):
            self.grid.setRowMinimumHeight(r, self.THUMB_SIZE)
        for r in range(rows, prev_rows):
            self.grid.setRowMinimumHeight(r, 0)
        for c in range(self._cols):
            self.grid.setColumnMinimumWidth(c, self.THUMB_SIZE)
        for c in range(self._cols, prev_cols):
            self.grid.setColumnMinimumWidth(c, 0)

        if rows > 0:
            total_height = rows * self.THUMB_SIZE + (rows - 1) * self.ROW_SPACING
        else:
            total_height = 0
        self.inner.setMinimumHeight(total_height)
        self.inner.setMaximumHeight(total_height)

    def _get_pixmap(self, thumb_path: str) -> QPixmap:
        if thumb_path in self._pixmap_cache:
            return self._pixmap_cache[thumb_path]
        pix = QPixmap(thumb_path)
        if pix.isNull():
            return QPixmap()
        pix = pix.scaled(self.THUMB_SIZE, self.THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._pixmap_cache[thumb_path] = pix
        self._pixmap_cache_order.append(thumb_path)
        if len(self._pixmap_cache_order) > self._pixmap_cache_max:
            old = self._pixmap_cache_order.popleft()
            self._pixmap_cache.pop(old, None)
        return pix

    def update_visible_thumbnails(self):
        area = self.scroll.viewport().rect()
        y0 = self.scroll.verticalScrollBar().value()
        y1 = y0 + area.height()
        thumb_h = self.THUMB_SIZE + self.ROW_SPACING
        first_row = max(0, y0 // thumb_h - 2)
        last_row = min((len(self.thumbs) + self._cols - 1) // self._cols, (y1 // thumb_h) + 2)
        # Remove labels not in visible range
        to_remove = [k for k in self.visible_labels if not (first_row <= k[0] < last_row)]
        for k in to_remove:
            label = self.visible_labels.pop(k)
            self.grid.removeWidget(label)
            label.deleteLater()
        # Add visible labels
        for row in range(first_row, last_row):
            for col in range(self._cols):
                idx = row * self._cols + col
                if idx >= len(self.thumbs):
                    break
                key = (row, col)
                if key not in self.visible_labels:
                    thumb_path = self.thumbs[idx]
                    img_path = self._image_path_for_index(idx)
                    label = QLabel()
                    label.setFixedSize(self.THUMB_SIZE, self.THUMB_SIZE)
                    label.setStyleSheet("background: #222; border: 1px solid #888;")
                    label.setAlignment(Qt.AlignCenter)
                    if os.path.exists(thumb_path):
                        pix = self._get_pixmap(thumb_path)
                        label.setPixmap(pix)
                    else:
                        label.setText("?")
                    if idx in self.selected_indices:
                        label.setStyleSheet("background: #444; border: 2px solid #00f;")
                    label.mousePressEvent = self._make_select_handler(idx)
                    self.grid.addWidget(label, row, col)
                    self.visible_labels[key] = label

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize and obj in (self.inner, self.scroll.viewport()):
            new_cols = self._compute_cols()
            if new_cols != self._cols:
                self.update_grid_geometry()
            self.update_visible_thumbnails()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        new_cols = self._compute_cols()
        if new_cols != self._cols:
            self.update_grid_geometry()
        self.update_visible_thumbnails()
        super().resizeEvent(event)

    def _make_select_handler(self, idx):
        def handler(event):
            self.setFocus()
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
                    img_path = self._image_path_for_index(idx)
                    self.image_selected.emit(img_path, self.thumbs[idx])
                    self.images_selected.emit(self.get_selected_images())
        return handler

    def keyPressEvent(self, event):
        if not self.thumbs:
            return
        idx = self._first_selected_index()
        if idx < 0:
            idx = 0
        new_idx = idx
        if event.key() == Qt.Key_Left:
            new_idx = max(0, idx - 1)
        elif event.key() == Qt.Key_Right:
            new_idx = min(len(self.thumbs) - 1, idx + 1)
        elif event.key() == Qt.Key_Up:
            new_idx = max(0, idx - max(1, self._cols))
        elif event.key() == Qt.Key_Down:
            new_idx = min(len(self.thumbs) - 1, idx + max(1, self._cols))
        elif event.key() == Qt.Key_Home:
            new_idx = 0
        elif event.key() == Qt.Key_End:
            new_idx = len(self.thumbs) - 1
        elif event.key() in (Qt.Key_PageUp, Qt.Key_PageDown):
            view_h = self.scroll.viewport().height()
            rows_per_page = max(1, view_h // (self.THUMB_SIZE + self.ROW_SPACING))
            delta = rows_per_page * max(1, self._cols)
            if event.key() == Qt.Key_PageUp:
                new_idx = max(0, idx - delta)
            else:
                new_idx = min(len(self.thumbs) - 1, idx + delta)
        else:
            return super().keyPressEvent(event)

        self.selected_indices = {new_idx}
        self.update_visible_thumbnails()
        self._ensure_visible(new_idx)
        img_path = self._image_path_for_index(new_idx)
        self.image_selected.emit(img_path, self.thumbs[new_idx])
        self.images_selected.emit(self.get_selected_images())

    def sizeHint(self):
        return QSize(1024, 600)
