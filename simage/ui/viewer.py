import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from simage.utils.paths import resolve_repo_path
from .record_filter import load_records
from .scanner import IMG_EXTS
from .theme import load_splitter_sizes, save_splitter_sizes


class ZoomableImageView(QGraphicsView):
    zoom_changed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._zoom = 100
        self._min_zoom = 10
        self._max_zoom = 1600
        self._scene = QGraphicsScene(self)
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)
        self.setScene(self._scene)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFrameShape(QFrame.Box)

    def has_image(self) -> bool:
        return not self._pixmap_item.pixmap().isNull()

    def image_size(self) -> Optional[tuple[int, int]]:
        pixmap = self._pixmap_item.pixmap()
        if pixmap.isNull():
            return None
        size = pixmap.size()
        return size.width(), size.height()

    def set_image_path(self, path: str) -> bool:
        if not path or not os.path.exists(path):
            self._clear_image()
            return False
        image = QImage(path)
        if image.isNull():
            self._clear_image()
            return False
        self.set_image_data(image, preserve_zoom=False)
        return True

    def set_image_data(self, image: QImage, preserve_zoom: bool = False) -> bool:
        if image is None or image.isNull():
            self._clear_image()
            return False
        center = self.mapToScene(self.viewport().rect().center())
        pixmap = QPixmap.fromImage(image)
        self._pixmap_item.setPixmap(pixmap)
        self._scene.setSceneRect(pixmap.rect())
        if preserve_zoom:
            zoom = self._zoom
            self.set_zoom_percent(zoom)
            self.centerOn(center)
        else:
            self.resetTransform()
            self._zoom = 100
            self.zoom_changed.emit(self._zoom)
            self.centerOn(self._pixmap_item)
        return True

    def _clear_image(self) -> None:
        self._pixmap_item.setPixmap(QPixmap())
        self._scene.setSceneRect(0, 0, 1, 1)
        self.resetTransform()
        self._zoom = 100
        self.zoom_changed.emit(self._zoom)

    def zoom_percent(self) -> int:
        return int(self._zoom)

    def set_zoom_percent(self, percent: int) -> None:
        if not self.has_image():
            return
        percent = int(max(self._min_zoom, min(self._max_zoom, percent)))
        self.resetTransform()
        scale = percent / 100.0
        self.scale(scale, scale)
        self._zoom = percent
        self.zoom_changed.emit(self._zoom)

    def step_zoom(self, delta: int) -> None:
        self.set_zoom_percent(self._zoom + delta)

    def fit_to_view(self) -> None:
        if not self.has_image():
            return
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
        scale = self.transform().m11()
        percent = int(max(self._min_zoom, min(self._max_zoom, round(scale * 100))))
        self._zoom = percent
        self.zoom_changed.emit(self._zoom)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.ControlModifier:
            step = 10 if event.angleDelta().y() > 0 else -10
            self.step_zoom(step)
            event.accept()
            return
        super().wheelEvent(event)


class ViewerTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.records_csv = str(resolve_repo_path("out/records.csv", must_exist=False, allow_absolute=False))
        self.input_dir = resolve_repo_path("Input", must_exist=False, allow_absolute=False)
        self._image_paths: List[str] = []
        self._list_controls: List[tuple[QListWidget, QLineEdit]] = []

        self._edit_original: Optional[QImage] = None
        self._edit_preview_base: Optional[QImage] = None
        self._edit_current_path = ""

        self._edit_preview_timer = QTimer(self)
        self._edit_preview_timer.setSingleShot(True)
        self._edit_preview_timer.timeout.connect(self._update_edit_preview)

        layout = QVBoxLayout(self)
        self._apply_page_layout(layout)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.single_tab = QWidget()
        self.compare_tab = QWidget()
        self.edit_tab = QWidget()
        self.tabs.addTab(self.single_tab, "Single View")
        self.tabs.addTab(self.compare_tab, "Compare")
        self.tabs.addTab(self.edit_tab, "Edit + Upscale")

        self._build_single_tab()
        self._build_compare_tab()
        self._build_edit_tab()

        self._refresh_all_image_lists()

    def _build_single_tab(self) -> None:
        layout = QVBoxLayout(self.single_tab)
        self._apply_tab_layout(layout)

        splitter = QSplitter(Qt.Horizontal)
        self.single_list_panel, self.single_list, self.single_filter = self._create_list_panel(
            "Images",
            refresh=True,
        )
        self.single_list.itemSelectionChanged.connect(self._on_single_selected)

        viewer_panel = QGroupBox("Viewer")
        viewer_layout = QVBoxLayout(viewer_panel)
        self._apply_section_layout(viewer_layout)
        viewer_header = QHBoxLayout()
        self.single_info = QLabel("No image selected.")
        self.single_info.setWordWrap(True)
        viewer_header.addWidget(self.single_info)
        viewer_header.addStretch(1)
        viewer_header.addWidget(
            self._help_button("Ctrl + mouse wheel to zoom. Drag to pan.")
        )
        viewer_layout.addLayout(viewer_header)

        self.single_view = ZoomableImageView()
        zoom_row = self._build_zoom_controls(self.single_view)
        viewer_layout.addLayout(zoom_row)
        viewer_layout.addWidget(self.single_view)

        splitter.addWidget(self.single_list_panel)
        splitter.addWidget(viewer_panel)
        self._init_splitter(splitter, "viewer/single", [280, 820])
        layout.addWidget(splitter)

    def _build_compare_tab(self) -> None:
        layout = QVBoxLayout(self.compare_tab)
        self._apply_tab_layout(layout)
        layout.setSpacing(12)

        refresh_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh image list")
        self._standard_button(refresh_btn)
        refresh_btn.clicked.connect(self._refresh_all_image_lists)
        refresh_row.addWidget(refresh_btn)
        refresh_row.addWidget(
            self._help_button("Reload images from out/records.csv or Input/.")
        )
        refresh_row.addStretch(1)
        layout.addLayout(refresh_row)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QGroupBox("Left Image")
        left_layout = QVBoxLayout(left_panel)
        self._apply_section_layout(left_layout)
        left_header = QHBoxLayout()
        self.compare_left_info = QLabel("No image selected.")
        self.compare_left_info.setWordWrap(True)
        left_header.addWidget(self.compare_left_info)
        left_header.addStretch(1)
        left_header.addWidget(self._help_button("Ctrl + mouse wheel to zoom left view."))
        left_layout.addLayout(left_header)
        self.compare_left_view = ZoomableImageView()
        left_layout.addLayout(self._build_zoom_controls(self.compare_left_view))
        left_layout.addWidget(self.compare_left_view)

        self.left_list_panel, self.compare_left_list, self.compare_left_filter = self._create_list_panel(
            "Select Left",
            refresh=False,
        )
        self.compare_left_list.itemSelectionChanged.connect(self._on_compare_left_selected)

        self.right_list_panel, self.compare_right_list, self.compare_right_filter = self._create_list_panel(
            "Select Right",
            refresh=False,
        )
        self.compare_right_list.itemSelectionChanged.connect(self._on_compare_right_selected)

        right_panel = QGroupBox("Right Image")
        right_layout = QVBoxLayout(right_panel)
        self._apply_section_layout(right_layout)
        right_header = QHBoxLayout()
        self.compare_right_info = QLabel("No image selected.")
        self.compare_right_info.setWordWrap(True)
        right_header.addWidget(self.compare_right_info)
        right_header.addStretch(1)
        right_header.addWidget(self._help_button("Ctrl + mouse wheel to zoom right view."))
        right_layout.addLayout(right_header)
        self.compare_right_view = ZoomableImageView()
        right_layout.addLayout(self._build_zoom_controls(self.compare_right_view))
        right_layout.addWidget(self.compare_right_view)

        splitter.addWidget(self.left_list_panel)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.addWidget(self.right_list_panel)
        self._init_splitter(splitter, "viewer/compare", [220, 420, 420, 220])
        layout.addWidget(splitter)

    def _build_edit_tab(self) -> None:
        layout = QVBoxLayout(self.edit_tab)
        self._apply_tab_layout(layout)

        splitter = QSplitter(Qt.Horizontal)

        self.edit_list_panel, self.edit_list, self.edit_filter = self._create_list_panel(
            "Images",
            refresh=True,
        )
        self.edit_list.itemSelectionChanged.connect(self._on_edit_selected)
        splitter.addWidget(self.edit_list_panel)

        preview_panel = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_panel)
        self._apply_section_layout(preview_layout)
        preview_header = QHBoxLayout()
        self.edit_info = QLabel("No image selected.")
        self.edit_info.setWordWrap(True)
        preview_header.addWidget(self.edit_info)
        preview_header.addStretch(1)
        preview_header.addWidget(self._help_button("Ctrl + mouse wheel to zoom."))
        preview_layout.addLayout(preview_header)
        self.edit_view = ZoomableImageView()
        preview_layout.addWidget(self.edit_view, 1)

        controls_panel = QWidget()
        controls_layout = QVBoxLayout(controls_panel)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(20)

        zoom_panel = QGroupBox("Zoom")
        zoom_layout = QVBoxLayout(zoom_panel)
        self._apply_section_layout(zoom_layout)
        zoom_layout.addLayout(self._build_zoom_controls(self.edit_view))
        controls_layout.addWidget(zoom_panel)

        adjustments_panel = QGroupBox("Adjustments")
        adjustments_layout = QVBoxLayout(adjustments_panel)
        self._apply_section_layout(adjustments_layout)
        self.brightness_slider, self.brightness_value = self._build_adjustment_row(
            "Brightness",
            adjustments_layout,
        )
        self.contrast_slider, self.contrast_value = self._build_adjustment_row(
            "Contrast",
            adjustments_layout,
        )
        self.saturation_slider, self.saturation_value = self._build_adjustment_row(
            "Saturation",
            adjustments_layout,
        )

        action_row = QHBoxLayout()
        self.reset_adjustments_btn = QPushButton("Reset Adjustments")
        self._standard_button(self.reset_adjustments_btn)
        self.reset_adjustments_btn.clicked.connect(self._reset_adjustments)
        self.save_adjustments_btn = QPushButton("Save Adjusted Copy")
        self._standard_button(self.save_adjustments_btn)
        self.save_adjustments_btn.clicked.connect(self._save_adjusted_copy)
        action_row.addWidget(self.reset_adjustments_btn)
        action_row.addWidget(self.save_adjustments_btn)
        action_row.addStretch(1)
        adjustments_layout.addLayout(action_row)
        controls_layout.addWidget(adjustments_panel)

        upscale_panel = QGroupBox("Upscale")
        upscale_layout = QVBoxLayout(upscale_panel)
        self._apply_section_layout(upscale_layout)
        upscale_row = QHBoxLayout()
        upscale_row.addWidget(QLabel("Scale"))
        self.upscale_combo = QComboBox()
        self.upscale_combo.addItems(["2x", "3x", "4x"])
        upscale_row.addWidget(self.upscale_combo)
        upscale_row.addStretch(1)
        upscale_layout.addLayout(upscale_row)
        self.save_upscale_btn = QPushButton("Save Upscaled Copy")
        self._standard_button(self.save_upscale_btn)
        self.save_upscale_btn.clicked.connect(self._save_upscaled_copy)
        upscale_layout.addWidget(self.save_upscale_btn)
        controls_layout.addWidget(upscale_panel)
        controls_layout.addStretch(1)

        splitter.addWidget(preview_panel)
        splitter.addWidget(controls_panel)
        self._init_splitter(splitter, "viewer/edit", [260, 760, 320])
        layout.addWidget(splitter)

        self._wire_adjustment_slider(self.brightness_slider, self.brightness_value)
        self._wire_adjustment_slider(self.contrast_slider, self.contrast_value)
        self._wire_adjustment_slider(self.saturation_slider, self.saturation_value)

    def _create_list_panel(self, title: str, refresh: bool) -> tuple[QGroupBox, QListWidget, QLineEdit]:
        panel = QGroupBox(title)
        layout = QVBoxLayout(panel)
        self._apply_section_layout(layout)

        filter_row = QHBoxLayout()
        filter_input = QLineEdit()
        filter_input.setPlaceholderText("Filter by name")
        filter_row.addWidget(filter_input)
        if refresh:
            refresh_btn = QPushButton("Refresh list")
            self._standard_button(refresh_btn)
            refresh_btn.clicked.connect(self._refresh_all_image_lists)
            filter_row.addWidget(refresh_btn)
        filter_row.addWidget(self._help_button("Filters the image list by filename."))
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        list_widget = QListWidget()
        list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(list_widget)

        self._register_image_list(list_widget, filter_input)
        return panel, list_widget, filter_input

    def _register_image_list(self, list_widget: QListWidget, filter_input: QLineEdit) -> None:
        self._list_controls.append((list_widget, filter_input))
        filter_input.textChanged.connect(
            lambda text, lw=list_widget: self._filter_image_list(lw, text)
        )

    def _filter_image_list(self, list_widget: QListWidget, text: str) -> None:
        current_path = self._current_list_path(list_widget)
        self._populate_image_list(list_widget, text, current_path)

    def _current_list_path(self, list_widget: QListWidget) -> str:
        items = list_widget.selectedItems()
        if not items:
            return ""
        data = items[0].data(Qt.UserRole)
        return str(data) if data else ""

    def _select_list_path(self, list_widget: QListWidget, path: str) -> None:
        if not path:
            return
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.data(Qt.UserRole) == path:
                list_widget.setCurrentRow(i)
                return

    def _populate_image_list(self, list_widget: QListWidget, text: str, keep_path: str) -> None:
        text = text.strip().lower()
        list_widget.blockSignals(True)
        list_widget.clear()
        for path in self._image_paths:
            name = os.path.basename(path)
            if text and text not in name.lower():
                continue
            item = QListWidgetItem(name)
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            list_widget.addItem(item)
        list_widget.blockSignals(False)
        if keep_path:
            self._select_list_path(list_widget, keep_path)
        if list_widget.count() > 0 and not list_widget.selectedItems():
            list_widget.setCurrentRow(0)

    def _refresh_all_image_lists(self) -> None:
        self._refresh_image_paths()
        for list_widget, filter_input in self._list_controls:
            current = self._current_list_path(list_widget)
            self._populate_image_list(list_widget, filter_input.text(), current)

    def _refresh_image_paths(self) -> None:
        paths = []
        if os.path.exists(self.records_csv):
            records = load_records(self.records_csv)
            for rec in records:
                img_path = rec.get("_image_path")
                if isinstance(img_path, str) and os.path.exists(img_path):
                    paths.append(img_path)
        if not paths and self.input_dir.exists():
            for entry in self.input_dir.iterdir():
                if entry.is_file() and entry.suffix.lower() in IMG_EXTS:
                    paths.append(str(entry.resolve()))
        seen = set()
        deduped = []
        for path in paths:
            if path in seen:
                continue
            seen.add(path)
            deduped.append(path)
        self._image_paths = sorted(deduped, key=lambda p: os.path.basename(p).lower())

    def _build_zoom_controls(self, view: ZoomableImageView) -> QHBoxLayout:
        row = QHBoxLayout()
        zoom_label = QLabel("Zoom: 100%")
        zoom_slider = QSlider(Qt.Horizontal)
        zoom_slider.setRange(10, 1600)
        zoom_slider.setValue(100)
        zoom_slider.setSingleStep(10)

        fit_btn = QPushButton("Fit")
        self._standard_button(fit_btn)
        actual_btn = QPushButton("100%")
        self._standard_button(actual_btn)
        zoom_out_btn = QPushButton("-")
        self._standard_button(zoom_out_btn)
        zoom_in_btn = QPushButton("+")
        self._standard_button(zoom_in_btn)

        zoom_slider.valueChanged.connect(lambda val: view.set_zoom_percent(val))
        view.zoom_changed.connect(
            lambda val, slider=zoom_slider, label=zoom_label: self._sync_zoom_controls(
                slider,
                label,
                val,
            )
        )
        fit_btn.clicked.connect(view.fit_to_view)
        actual_btn.clicked.connect(lambda: view.set_zoom_percent(100))
        zoom_out_btn.clicked.connect(lambda: view.step_zoom(-10))
        zoom_in_btn.clicked.connect(lambda: view.step_zoom(10))

        row.addWidget(zoom_out_btn)
        row.addWidget(zoom_in_btn)
        row.addWidget(actual_btn)
        row.addWidget(fit_btn)
        row.addWidget(zoom_label)
        row.addWidget(zoom_slider)
        row.addStretch(1)
        return row

    def _sync_zoom_controls(self, slider: QSlider, label: QLabel, value: int) -> None:
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)
        label.setText(f"Zoom: {value}%")

    def _update_info_label(self, label: QLabel, path: str, view: ZoomableImageView) -> None:
        if not path:
            label.setText("No image selected.")
            label.setToolTip("")
            return
        size = view.image_size()
        if size:
            width, height = size
            label.setText(f"{os.path.basename(path)}  |  {width} x {height}")
        else:
            label.setText(os.path.basename(path))
        label.setToolTip(path)

    def _on_single_selected(self) -> None:
        items = self.single_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        if not isinstance(path, str):
            return
        if self.single_view.set_image_path(path):
            self.single_view.fit_to_view()
        self._update_info_label(self.single_info, path, self.single_view)

    def _on_compare_left_selected(self) -> None:
        items = self.compare_left_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        if not isinstance(path, str):
            return
        if self.compare_left_view.set_image_path(path):
            self.compare_left_view.fit_to_view()
        self._update_info_label(self.compare_left_info, path, self.compare_left_view)

    def _on_compare_right_selected(self) -> None:
        items = self.compare_right_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        if not isinstance(path, str):
            return
        if self.compare_right_view.set_image_path(path):
            self.compare_right_view.fit_to_view()
        self._update_info_label(self.compare_right_info, path, self.compare_right_view)

    def _on_edit_selected(self) -> None:
        items = self.edit_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        if not isinstance(path, str):
            return
        self._load_edit_image(path)

    def _load_edit_image(self, path: str) -> None:
        if not path or not os.path.exists(path):
            self._edit_original = None
            self._edit_preview_base = None
            self._edit_current_path = ""
            self.edit_view.set_image_data(QImage(), preserve_zoom=False)
            self._update_info_label(self.edit_info, "", self.edit_view)
            return
        image = QImage(path)
        if image.isNull():
            QMessageBox.warning(self, "Image Error", "Unable to load the selected image.")
            return
        self._edit_original = image
        self._edit_current_path = path
        self._edit_preview_base = self._scaled_preview(image)
        self.edit_view.set_image_data(self._edit_preview_base, preserve_zoom=False)
        self.edit_view.fit_to_view()
        self._update_info_label(self.edit_info, path, self.edit_view)
        self._reset_adjustments(update_preview=False)

    def _scaled_preview(self, image: QImage) -> QImage:
        max_dim = 1600
        if image.width() <= max_dim and image.height() <= max_dim:
            return image
        return image.scaled(max_dim, max_dim, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _build_adjustment_row(self, label: str, parent_layout: QVBoxLayout) -> tuple[QSlider, QLabel]:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        slider = QSlider(Qt.Horizontal)
        slider.setRange(-100, 100)
        slider.setValue(0)
        slider.setSingleStep(5)
        value_label = QLabel("0")
        value_label.setMinimumWidth(32)
        row.addWidget(slider)
        row.addWidget(value_label)
        row.addStretch(1)
        parent_layout.addLayout(row)
        return slider, value_label

    def _wire_adjustment_slider(self, slider: QSlider, value_label: QLabel) -> None:
        slider.valueChanged.connect(lambda val: value_label.setText(str(val)))
        slider.valueChanged.connect(lambda _val: self._schedule_edit_preview())

    def _schedule_edit_preview(self) -> None:
        if not self._edit_preview_base:
            return
        self._edit_preview_timer.start(150)

    def _update_edit_preview(self) -> None:
        if not self._edit_preview_base:
            return
        brightness = self.brightness_slider.value()
        contrast = self.contrast_slider.value()
        saturation = self.saturation_slider.value()
        adjusted = self._apply_adjustments(self._edit_preview_base, brightness, contrast, saturation)
        self.edit_view.set_image_data(adjusted, preserve_zoom=True)

    def _reset_adjustments(self, update_preview: bool = True) -> None:
        self.brightness_slider.blockSignals(True)
        self.contrast_slider.blockSignals(True)
        self.saturation_slider.blockSignals(True)
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(0)
        self.saturation_slider.setValue(0)
        self.brightness_slider.blockSignals(False)
        self.contrast_slider.blockSignals(False)
        self.saturation_slider.blockSignals(False)
        self.brightness_value.setText("0")
        self.contrast_value.setText("0")
        self.saturation_value.setText("0")
        if update_preview and self._edit_preview_base:
            self.edit_view.set_image_data(self._edit_preview_base, preserve_zoom=True)

    def _save_adjusted_copy(self) -> None:
        if not self._edit_original or not self._edit_current_path:
            QMessageBox.information(self, "No Image", "Select an image to adjust.")
            return
        brightness = self.brightness_slider.value()
        contrast = self.contrast_slider.value()
        saturation = self.saturation_slider.value()
        adjusted = self._apply_adjustments(self._edit_original, brightness, contrast, saturation)
        output_path = self._suggest_output_path(self._edit_current_path, "_edited")
        if adjusted.save(output_path):
            QMessageBox.information(self, "Saved", f"Adjusted copy saved to:\n{output_path}")
        else:
            QMessageBox.warning(self, "Save Failed", "Unable to save the adjusted image.")

    def _save_upscaled_copy(self) -> None:
        if not self._edit_original or not self._edit_current_path:
            QMessageBox.information(self, "No Image", "Select an image to upscale.")
            return
        factor_text = self.upscale_combo.currentText().replace("x", "")
        try:
            factor = int(factor_text)
        except ValueError:
            factor = 2
        width = self._edit_original.width() * factor
        height = self._edit_original.height() * factor
        scaled = self._edit_original.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        output_path = self._suggest_output_path(self._edit_current_path, f"_upscale_{factor}x")
        if scaled.save(output_path):
            QMessageBox.information(self, "Saved", f"Upscaled copy saved to:\n{output_path}")
        else:
            QMessageBox.warning(self, "Save Failed", "Unable to save the upscaled image.")

    def _suggest_output_path(self, original_path: str, suffix: str) -> str:
        original = Path(original_path)
        candidate = original.with_name(f"{original.stem}{suffix}{original.suffix}")
        if not candidate.exists():
            return str(candidate)
        idx = 2
        while True:
            candidate = original.with_name(f"{original.stem}{suffix}_{idx}{original.suffix}")
            if not candidate.exists():
                return str(candidate)
            idx += 1

    def _apply_adjustments(self, image: QImage, brightness: int, contrast: int, saturation: int) -> QImage:
        # Simple per-pixel adjustments for brightness, contrast, and saturation.
        if image.isNull():
            return image
        out = image.convertToFormat(QImage.Format_ARGB32)
        width = out.width()
        height = out.height()
        contrast_factor = 1.0 + (contrast / 100.0)
        saturation_factor = 1.0 + (saturation / 100.0)
        brightness = int(brightness)

        for y in range(height):
            for x in range(width):
                color = out.pixelColor(x, y)
                r = int(((color.red() - 128) * contrast_factor) + 128 + brightness)
                g = int(((color.green() - 128) * contrast_factor) + 128 + brightness)
                b = int(((color.blue() - 128) * contrast_factor) + 128 + brightness)
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                if saturation != 0:
                    adj = QColor(r, g, b, color.alpha())
                    h, s, v, a = adj.getHsv()
                    if h >= 0:
                        s = int(max(0, min(255, s * saturation_factor)))
                        adj.setHsv(h, s, v, a)
                    out.setPixelColor(x, y, adj)
                else:
                    out.setPixelColor(x, y, QColor(r, g, b, color.alpha()))
        return out

    def _help_button(self, text: str) -> QToolButton:
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
        layout.setContentsMargins(40, 16, 40, 20)
        layout.setSpacing(20)

    def _apply_section_layout(self, layout: QVBoxLayout) -> None:
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

    def _apply_tab_layout(self, layout: QVBoxLayout) -> None:
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(28)

    def _init_splitter(self, splitter: QSplitter, key: str, fallback: list[int]) -> None:
        sizes = load_splitter_sizes(key)
        if sizes and len(sizes) == splitter.count():
            splitter.setSizes(sizes)
        else:
            splitter.setSizes(fallback)
        splitter.splitterMoved.connect(
            lambda _pos, _idx, sp=splitter, k=key: self._save_splitter(sp, k)
        )

    def _save_splitter(self, splitter: QSplitter, key: str) -> None:
        save_splitter_sizes(key, splitter.sizes())
