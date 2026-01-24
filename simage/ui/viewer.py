import copy  # DIFF-003-001
import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QEvent, Qt, QTimer, Signal  # DIFF-003-007
from PySide6.QtGui import (  # DIFF-003-001
    QColor,
    QImage,
    QKeySequence,
    QPainter,
    QPixmap,
    QShortcut,
    QTransform,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,  # DIFF-003-008
    QComboBox,
    QColorDialog,  # DIFF-003-006
    QDialog,  # DIFF-003-006
    QDialogButtonBox,  # DIFF-003-006
    QDoubleSpinBox,  # DIFF-003-006
    QFrame,
    QFormLayout,  # DIFF-003-006
    QGridLayout,
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
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,  # DIFF-003-006
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from simage.utils.paths import resolve_repo_path
from .record_filter import load_records
from .scanner import IMG_EXTS
from .theme import (  # DIFF-001-001
    UI_INNER_GAP,  # DIFF-001-001
    UI_OUTER_PADDING,  # DIFF-001-001
    UI_SECTION_GAP,  # DIFF-001-001
    load_splitter_sizes,  # DIFF-001-001
    save_splitter_sizes,  # DIFF-001-001
)

EDIT_SLIDER_SECTIONS = [
    (
        "Basic tone",
        [
            {"key": "exposure", "label": "Exposure", "min": -5.0, "max": 5.0, "step": 0.1, "default": 0.0, "scale": 10},
            {"key": "brightness", "label": "Brightness", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "contrast", "label": "Contrast", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "gamma", "label": "Gamma", "min": 0.1, "max": 3.0, "step": 0.1, "default": 1.0, "scale": 10},
            {"key": "black_point", "label": "Black Point", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "white_point", "label": "White Point", "min": -100, "max": 100, "step": 1, "default": 0},
        ],
    ),
    (
        "Highlights & shadows",
        [
            {"key": "highlights", "label": "Highlights", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "shadows", "label": "Shadows", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "whites", "label": "Whites", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "blacks", "label": "Blacks", "min": -100, "max": 100, "step": 1, "default": 0},
        ],
    ),
    (
        "Color / white balance",
        [
            {
                "key": "temperature",
                "label": "Temperature (Kelvin / Warmth)",
                "min": 2000,
                "max": 12000,
                "step": 100,
                "default": 6500,
                "scale": 1,
                "suffix": " K",
            },
            {"key": "tint", "label": "Tint (Green-Magenta)", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "saturation", "label": "Saturation", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "vibrance", "label": "Vibrance", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "hue", "label": "Hue", "min": -180, "max": 180, "step": 1, "default": 0, "suffix": " deg"},
        ],
    ),
    (
        "Detail / sharpness",
        [
            {"key": "sharpening", "label": "Sharpening", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "sharpen_radius", "label": "Sharpen Radius", "min": 0.1, "max": 5.0, "step": 0.1, "default": 1.0, "scale": 10},
            {"key": "sharpen_amount", "label": "Sharpen Amount", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "sharpen_threshold", "label": "Sharpen Threshold", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "detail", "label": "Detail", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "edge_masking", "label": "Edge Masking", "min": 0, "max": 100, "step": 1, "default": 0},
        ],
    ),
    (
        "Texture / micro-contrast",
        [
            {"key": "clarity", "label": "Clarity", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "texture", "label": "Texture", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "structure", "label": "Structure", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "midtone_contrast", "label": "Midtone Contrast", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "local_contrast", "label": "Local Contrast", "min": -100, "max": 100, "step": 1, "default": 0},
        ],
    ),
    (
        "Noise / smoothing",
        [
            {"key": "noise_reduction_luma", "label": "Noise Reduction (Luminance)", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "noise_reduction_color", "label": "Noise Reduction (Color)", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "denoise_amount", "label": "Denoise Amount", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "denoise_detail", "label": "Denoise Detail", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "grain_reduction", "label": "Grain Reduction", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "skin_smoothing", "label": "Smoothing / Skin Smoothing", "min": 0, "max": 100, "step": 1, "default": 0},
        ],
    ),
    (
        "Dehaze / atmospheric",
        [
            {"key": "dehaze", "label": "Dehaze", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "haze_removal", "label": "Haze Removal", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "defog", "label": "Defog", "min": -100, "max": 100, "step": 1, "default": 0},
        ],
    ),
    (
        "Effects",
        [
            {"key": "vignette", "label": "Vignette", "min": -100, "max": 100, "step": 1, "default": 0},
            {"key": "fade", "label": "Fade", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "grain", "label": "Grain", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "glow", "label": "Glow / Bloom", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "lens_blur", "label": "Lens Blur", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "motion_blur", "label": "Motion Blur", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "unsharp_mask", "label": "Sharpen (Unsharp Mask)", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "high_pass", "label": "High Pass", "min": 0, "max": 100, "step": 1, "default": 0},
            {"key": "clarity_pop", "label": "Clarity/Pop", "min": 0, "max": 100, "step": 1, "default": 0},
        ],
    ),
]

EDIT_PLACEHOLDER_SECTIONS = [
    ("Tone curve", ["Tone Curve (RGB)", "Channel Curves (R / G / B)"]),
    ("HSL / color mix", ["Hue (per color)", "Saturation (per color)", "Luminance (per color)"]),
    (
        "Color grading",
        [
            "Shadows Color",
            "Midtones Color",
            "Highlights Color",
            "Balance",
            "Split Toning (Highlight Hue/Sat, Shadow Hue/Sat)",
        ],
    ),
    ("Levels / channel controls", ["Levels (Input/Output)", "RGB Levels", "Individual Channel Levels"]),
    (
        "Geometry / transform",
        [
            "Crop",
            "Rotate",
            "Straighten",
            "Perspective (Vertical/Horizontal)",
            "Distort / Warp",
            "Scale",
            "Flip Horizontal / Vertical",
        ],
    ),
]

HSL_COLOR_BANDS = [  # DIFF-003-003
    "red",  # DIFF-003-003
    "orange",  # DIFF-003-003
    "yellow",  # DIFF-003-003
    "green",  # DIFF-003-003
    "aqua",  # DIFF-003-003
    "blue",  # DIFF-003-003
    "purple",  # DIFF-003-003
    "magenta",  # DIFF-003-003
]


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
        self._edit_working_preview: Optional[QImage] = None  # DIFF-003-001
        self._edit_current_path = ""

        self._edit_preview_timer = QTimer(self)
        self._edit_preview_timer.setSingleShot(True)
        self._edit_preview_timer.timeout.connect(self._update_edit_preview)
        self._edit_state_timer = QTimer(self)  # DIFF-003-001
        self._edit_state_timer.setSingleShot(True)  # DIFF-003-001
        self._edit_state_timer.timeout.connect(self._commit_edit_state)  # DIFF-003-001
        self._undo_stack: List[dict] = []  # DIFF-003-001
        self._redo_stack: List[dict] = []  # DIFF-003-001
        self._history_limit = 20  # DIFF-003-001
        self._current_state: Optional[dict] = None  # DIFF-003-001
        self._suppress_state_commit = False  # DIFF-003-001
        self._advanced_settings = self._default_advanced_settings()  # DIFF-003-006
        self._geometry_settings = self._default_geometry_settings()  # DIFF-003-007
        self._brush_mask: Optional[QImage] = None  # DIFF-003-007
        self._brush_painting = False  # DIFF-003-007
        self._brush_dirty = False  # DIFF-003-007

        layout = QVBoxLayout(self)
        self._apply_page_layout(layout)

        self._build_unified_viewer(layout)  # DIFF-002-001

        self._refresh_all_image_lists()  # DIFF-002-001

        self._init_edit_shortcuts()  # DIFF-003-001

    def _build_unified_viewer(self, layout: QVBoxLayout) -> None:  # DIFF-002-001
        main_splitter = QSplitter(Qt.Vertical)  # DIFF-002-001

        list_splitter = QSplitter(Qt.Horizontal)  # DIFF-002-001
        self.left_list_panel, self.compare_left_list, self.compare_left_filter = self._create_list_panel(  # DIFF-002-001
            "Left Image",  # DIFF-002-001
            refresh=True,  # DIFF-002-001
        )
        self.left_list_panel.setMinimumWidth(240)  # DIFF-002-006
        self.compare_left_list.itemSelectionChanged.connect(self._on_compare_left_selected)  # DIFF-002-001
        self.edit_list_panel, self.edit_list, self.edit_filter = self._create_list_panel(  # DIFF-002-001
            "Right Image",  # DIFF-002-001
            refresh=False,  # DIFF-002-001
        )
        self.edit_list_panel.setMinimumWidth(240)  # DIFF-002-006
        self.edit_list.itemSelectionChanged.connect(self._on_edit_selected)  # DIFF-002-005
        list_splitter.addWidget(self.left_list_panel)  # DIFF-002-001
        list_splitter.addWidget(self.edit_list_panel)  # DIFF-002-001
        list_splitter.setStretchFactor(0, 1)  # DIFF-002-006
        list_splitter.setStretchFactor(1, 1)  # DIFF-002-006
        main_splitter.addWidget(list_splitter)  # DIFF-002-001

        content_splitter = QSplitter(Qt.Horizontal)  # DIFF-002-001

        image_splitter = QSplitter(Qt.Horizontal)  # DIFF-002-001

        left_panel = QGroupBox("Left Image")  # DIFF-002-001
        left_panel.setMinimumWidth(480)  # DIFF-002-006
        left_panel_layout = QVBoxLayout(left_panel)  # DIFF-002-001
        self._apply_section_layout(left_panel_layout)  # DIFF-002-001
        left_header = QHBoxLayout()  # DIFF-002-001
        self.compare_left_info = QLabel("No image selected.")  # DIFF-002-001
        self.compare_left_info.setWordWrap(True)  # DIFF-002-001
        left_header.addWidget(self.compare_left_info)  # DIFF-002-001
        left_header.addStretch(1)  # DIFF-002-001
        left_header.addWidget(self._help_button("Ctrl + mouse wheel to zoom left view."))  # DIFF-002-001
        left_panel_layout.addLayout(left_header)  # DIFF-002-001
        self.compare_left_view = ZoomableImageView()  # DIFF-002-001
        left_body = QHBoxLayout()  # DIFF-002-001
        left_body.setSpacing(UI_INNER_GAP)  # DIFF-002-001
        left_body.addWidget(self._build_vertical_zoom_controls(self.compare_left_view))  # DIFF-002-002
        left_body.addWidget(self.compare_left_view, 1)  # DIFF-002-001
        left_panel_layout.addLayout(left_body)  # DIFF-002-001

        right_panel = QGroupBox("Right Image")  # DIFF-002-001
        right_panel.setMinimumWidth(480)  # DIFF-002-006
        right_panel_layout = QVBoxLayout(right_panel)  # DIFF-002-001
        self._apply_section_layout(right_panel_layout)  # DIFF-002-001
        right_header = QHBoxLayout()  # DIFF-002-001
        self.edit_info = QLabel("No image selected.")  # DIFF-002-001
        self.edit_info.setWordWrap(True)  # DIFF-002-001
        right_header.addWidget(self.edit_info)  # DIFF-002-001
        right_header.addStretch(1)  # DIFF-002-001
        right_header.addWidget(self._help_button("Ctrl + mouse wheel to zoom right view."))  # DIFF-002-001
        right_panel_layout.addLayout(right_header)  # DIFF-002-001
        self.edit_view = ZoomableImageView()  # DIFF-002-005
        self.edit_view.viewport().installEventFilter(self)  # DIFF-003-007
        self.edit_view.setMouseTracking(True)  # DIFF-003-007
        right_body = QHBoxLayout()  # DIFF-002-001
        right_body.setSpacing(UI_INNER_GAP)  # DIFF-002-001
        right_body.addWidget(self.edit_view, 1)  # DIFF-002-001
        right_body.addWidget(self._build_vertical_zoom_controls(self.edit_view))  # DIFF-002-003
        right_panel_layout.addLayout(right_body)  # DIFF-002-001

        image_splitter.addWidget(left_panel)  # DIFF-002-001
        image_splitter.addWidget(right_panel)  # DIFF-002-001
        image_splitter.setStretchFactor(0, 1)  # DIFF-002-006
        image_splitter.setStretchFactor(1, 1)  # DIFF-002-006
        content_splitter.addWidget(image_splitter)  # DIFF-002-001

        controls_panel = QGroupBox("Edit controls (Right image).")  # DIFF-002-004
        controls_layout = QVBoxLayout(controls_panel)  # DIFF-002-004
        self._apply_section_layout(controls_layout)  # DIFF-002-004

        adjustments_panel = QGroupBox("Adjustments")  # DIFF-002-004
        adjustments_layout = QVBoxLayout(adjustments_panel)  # DIFF-002-004
        self._apply_section_layout(adjustments_layout)  # DIFF-002-004
        self._build_adjustment_controls(adjustments_layout)  # DIFF-002-004

        action_row = QHBoxLayout()  # DIFF-002-004
        self.reset_adjustments_btn = QPushButton("Reset Adjustments")  # DIFF-002-004
        self._standard_button(self.reset_adjustments_btn)  # DIFF-002-004
        self.reset_adjustments_btn.clicked.connect(self._reset_adjustments)  # DIFF-002-004
        self.save_adjustments_btn = QPushButton("Save Adjusted Copy")  # DIFF-002-004
        self._standard_button(self.save_adjustments_btn)  # DIFF-002-004
        self.save_adjustments_btn.clicked.connect(self._save_adjusted_copy)  # DIFF-002-004
        action_row.addWidget(self.reset_adjustments_btn)  # DIFF-002-004
        action_row.addWidget(self.save_adjustments_btn)  # DIFF-002-004
        action_row.addStretch(1)  # DIFF-002-004
        adjustments_layout.addLayout(action_row)  # DIFF-002-004
        controls_layout.addWidget(adjustments_panel)  # DIFF-002-004

        upscale_panel = QGroupBox("Upscale")  # DIFF-002-004
        upscale_layout = QVBoxLayout(upscale_panel)  # DIFF-002-004
        self._apply_section_layout(upscale_layout)  # DIFF-002-004
        upscale_row = QHBoxLayout()  # DIFF-002-004
        upscale_row.addWidget(QLabel("Scale"))  # DIFF-002-004
        self.upscale_combo = QComboBox()  # DIFF-002-004
        self.upscale_combo.addItems(["2x", "3x", "4x"])  # DIFF-002-004
        upscale_row.addWidget(self.upscale_combo)  # DIFF-002-004
        upscale_row.addStretch(1)  # DIFF-002-004
        upscale_layout.addLayout(upscale_row)  # DIFF-002-004
        self.save_upscale_btn = QPushButton("Save Upscaled Copy")  # DIFF-002-004
        self._standard_button(self.save_upscale_btn)  # DIFF-002-004
        self.save_upscale_btn.clicked.connect(self._save_upscaled_copy)  # DIFF-002-004
        upscale_layout.addWidget(self.save_upscale_btn)  # DIFF-002-004
        controls_layout.addWidget(upscale_panel)  # DIFF-002-004

        output_panel = QGroupBox("Output / Save Options")  # DIFF-003-008
        output_layout = QVBoxLayout(output_panel)  # DIFF-003-008
        self._apply_section_layout(output_layout)  # DIFF-003-008
        self.keep_original_checkbox = QCheckBox("Affect copy only / keep original")  # DIFF-003-008
        self.keep_original_checkbox.setChecked(True)  # DIFF-003-008
        output_layout.addWidget(self.keep_original_checkbox)  # DIFF-003-008
        controls_layout.addWidget(output_panel)  # DIFF-003-008

        controls_scroll = QScrollArea()  # DIFF-002-004
        controls_scroll.setWidgetResizable(True)  # DIFF-002-004
        controls_scroll.setFrameShape(QFrame.NoFrame)  # DIFF-002-004
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # DIFF-002-004
        controls_scroll.setWidget(controls_panel)  # DIFF-002-004
        controls_scroll.setMinimumWidth(320)  # DIFF-002-006
        content_splitter.addWidget(controls_scroll)  # DIFF-002-004
        content_splitter.setStretchFactor(0, 3)  # DIFF-002-006
        content_splitter.setStretchFactor(1, 1)  # DIFF-002-006
        main_splitter.addWidget(content_splitter)  # DIFF-002-001

        self._init_splitter(main_splitter, "viewer/unified", [220, 780])  # DIFF-002-006
        main_splitter.setStretchFactor(0, 1)  # DIFF-002-006
        main_splitter.setStretchFactor(1, 3)  # DIFF-002-006
        layout.addWidget(main_splitter)  # DIFF-002-001

    def _build_single_tab(self) -> None:
        layout = QVBoxLayout(self.single_tab)
        self._apply_tab_layout(layout)

        splitter = QSplitter(Qt.Horizontal)
        self.single_list_panel, self.single_list, self.single_filter = self._create_list_panel(
            "Images",
            refresh=True,
        )
        self.single_list_panel.setMinimumWidth(240)  # DIFF-001-003
        self.single_list.itemSelectionChanged.connect(self._on_single_selected)

        viewer_panel = QGroupBox("Viewer")
        viewer_panel.setMinimumWidth(480)  # DIFF-001-003
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
        splitter.setStretchFactor(0, 1)  # DIFF-001-005
        splitter.setStretchFactor(1, 3)  # DIFF-001-005
        layout.addWidget(splitter)

    def _build_compare_tab(self) -> None:
        layout = QVBoxLayout(self.compare_tab)
        self._apply_tab_layout(layout)
        layout.setSpacing(UI_SECTION_GAP)  # DIFF-001-001

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
        left_panel.setMinimumWidth(480)  # DIFF-001-003
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
        self.left_list_panel.setMinimumWidth(240)  # DIFF-001-003
        self.compare_left_list.itemSelectionChanged.connect(self._on_compare_left_selected)

        self.right_list_panel, self.compare_right_list, self.compare_right_filter = self._create_list_panel(
            "Select Right",
            refresh=False,
        )
        self.right_list_panel.setMinimumWidth(240)  # DIFF-001-003
        self.compare_right_list.itemSelectionChanged.connect(self._on_compare_right_selected)

        right_panel = QGroupBox("Right Image")
        right_panel.setMinimumWidth(480)  # DIFF-001-003
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
        self._init_splitter(splitter, "viewer/compare", [240, 480, 480, 240])  # DIFF-001-005
        splitter.setStretchFactor(0, 1)  # DIFF-001-005
        splitter.setStretchFactor(1, 3)  # DIFF-001-005
        splitter.setStretchFactor(2, 3)  # DIFF-001-005
        splitter.setStretchFactor(3, 1)  # DIFF-001-005
        layout.addWidget(splitter)

    def _build_edit_tab(self) -> None:
        layout = QVBoxLayout(self.edit_tab)
        self._apply_tab_layout(layout)

        splitter = QSplitter(Qt.Horizontal)

        self.edit_list_panel, self.edit_list, self.edit_filter = self._create_list_panel(
            "Images",
            refresh=True,
        )
        self.edit_list_panel.setMinimumWidth(240)  # DIFF-001-003
        self.edit_list.itemSelectionChanged.connect(self._on_edit_selected)
        splitter.addWidget(self.edit_list_panel)

        preview_panel = QGroupBox("Preview")
        preview_panel.setMinimumWidth(480)  # DIFF-001-003
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
        controls_layout.setSpacing(UI_SECTION_GAP)  # DIFF-001-001

        zoom_panel = QGroupBox("Zoom")
        zoom_layout = QVBoxLayout(zoom_panel)
        self._apply_section_layout(zoom_layout)
        zoom_layout.addLayout(self._build_zoom_controls(self.edit_view))
        controls_layout.addWidget(zoom_panel)

        adjustments_panel = QGroupBox("Adjustments")
        adjustments_layout = QVBoxLayout(adjustments_panel)
        self._apply_section_layout(adjustments_layout)
        self._build_adjustment_controls(adjustments_layout)

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
        controls_scroll = QScrollArea()  # DIFF-001-004
        controls_scroll.setWidgetResizable(True)  # DIFF-001-004
        controls_scroll.setFrameShape(QFrame.NoFrame)  # DIFF-001-004
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # DIFF-001-004
        controls_scroll.setWidget(controls_panel)  # DIFF-001-004
        controls_scroll.setMinimumWidth(320)  # DIFF-001-003
        splitter.addWidget(controls_scroll)  # DIFF-001-004
        self._init_splitter(splitter, "viewer/edit", [260, 760, 320])
        splitter.setStretchFactor(0, 1)  # DIFF-001-005
        splitter.setStretchFactor(1, 3)  # DIFF-001-005
        splitter.setStretchFactor(2, 1)  # DIFF-001-005
        layout.addWidget(splitter)

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

    def _build_vertical_zoom_controls(self, view: ZoomableImageView) -> QWidget:  # DIFF-002-002
        container = QWidget()  # DIFF-002-002
        layout = QVBoxLayout(container)  # DIFF-002-002
        layout.setContentsMargins(0, 0, 0, 0)  # DIFF-002-002
        layout.setSpacing(UI_INNER_GAP)  # DIFF-002-002
        zoom_label = QLabel("Zoom: 100%")  # DIFF-002-002
        zoom_label.setAlignment(Qt.AlignCenter)  # DIFF-002-002
        zoom_slider = QSlider(Qt.Vertical)  # DIFF-002-002
        zoom_slider.setRange(10, 1600)  # DIFF-002-002
        zoom_slider.setValue(100)  # DIFF-002-002
        zoom_slider.setSingleStep(10)  # DIFF-002-002
        zoom_slider.setPageStep(50)  # DIFF-002-002
        zoom_slider.setMinimumHeight(160)  # DIFF-002-002
        zoom_slider.setFixedWidth(26)  # DIFF-002-002
        zoom_slider.valueChanged.connect(lambda val: view.set_zoom_percent(val))  # DIFF-002-002
        view.zoom_changed.connect(lambda val, slider=zoom_slider, label=zoom_label: self._sync_zoom_controls(slider, label, val))  # DIFF-002-002
        layout.addWidget(zoom_slider, 1)  # DIFF-002-002
        layout.addWidget(zoom_label)  # DIFF-002-002
        return container  # DIFF-002-002

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
            self._edit_working_preview = None  # DIFF-003-001
            self._edit_current_path = ""
            self.edit_view.set_image_data(QImage(), preserve_zoom=False)
            self._update_info_label(self.edit_info, "", self.edit_view)
            self._undo_stack.clear()  # DIFF-003-001
            self._redo_stack.clear()  # DIFF-003-001
            self._current_state = None  # DIFF-003-001
            return
        image = QImage(path)
        if image.isNull():
            QMessageBox.warning(self, "Image Error", "Unable to load the selected image.")
            return
        self._edit_original = image
        self._edit_current_path = path
        self._edit_preview_base = self._scaled_preview(image)
        self._edit_working_preview = self._edit_preview_base  # DIFF-003-001
        self.edit_view.set_image_data(self._edit_preview_base, preserve_zoom=False)
        self.edit_view.fit_to_view()
        self._update_info_label(self.edit_info, path, self.edit_view)
        self._reset_adjustments(update_preview=False)

    def _scaled_preview(self, image: QImage) -> QImage:
        max_dim = 1600
        if image.width() <= max_dim and image.height() <= max_dim:
            return image
        return image.scaled(max_dim, max_dim, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _build_adjustment_controls(self, parent_layout: QVBoxLayout) -> None:
        self._adjustment_sliders = {}
        self._adjustment_value_labels = {}
        self._adjustment_defaults = {}
        self._adjustment_scales = {}
        self._adjustment_suffixes = {}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(UI_SECTION_GAP)  # DIFF-001-001
        scroll.setWidget(container)
        parent_layout.addWidget(scroll, 1)

        for section_label, adjustments in EDIT_SLIDER_SECTIONS:
            self._add_adjustment_section_label(container_layout, section_label)
            for adj in adjustments:
                slider, value_label = self._build_adjustment_row(
                    adj["label"],
                    container_layout,
                    min_val=adj.get("min", -100),
                    max_val=adj.get("max", 100),
                    step=adj.get("step", 1),
                    default=adj.get("default", 0),
                    scale=adj.get("scale", 1),
                    suffix=adj.get("suffix", ""),
                )
                self._register_adjustment_slider(adj["key"], slider, value_label, adj)
            container_layout.addSpacing(6)

        self._add_adjustment_section_label(container_layout, "Brush")  # DIFF-003-007
        self._build_brush_controls(container_layout)  # DIFF-003-007
        container_layout.addSpacing(6)

        for section_label, buttons in EDIT_PLACEHOLDER_SECTIONS:
            self._add_adjustment_section_label(container_layout, section_label)  # DIFF-003-006
            self._add_placeholder_buttons(container_layout, buttons)  # DIFF-003-006
            container_layout.addSpacing(6)

        container_layout.addStretch(1)

    def _add_adjustment_section_label(self, parent_layout: QVBoxLayout, text: str) -> None:
        label = QLabel(text)
        label.setStyleSheet("font-weight: 600;")
        parent_layout.addWidget(label)

    def _add_placeholder_buttons(self, parent_layout: QVBoxLayout, labels: List[str]) -> None:
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        for idx, text in enumerate(labels):
            row = idx // 2
            col = idx % 2
            btn = QPushButton(text)
            self._standard_button(btn)
            action = self._placeholder_action_for_label(text)  # DIFF-003-006
            if action:  # DIFF-003-006
                btn.clicked.connect(action)  # DIFF-003-006
                btn.setToolTip("Open settings.")  # DIFF-003-006
            else:  # DIFF-003-006
                btn.setToolTip("Control not wired.")  # DIFF-003-006
            grid.addWidget(btn, row, col)
        parent_layout.addLayout(grid)

    def _placeholder_action_for_label(self, label: str):  # DIFF-003-006
        if label == "Tone Curve (RGB)":  # DIFF-003-006
            return self._open_tone_curve_dialog  # DIFF-003-006
        if label == "Channel Curves (R / G / B)":  # DIFF-003-006
            return self._open_channel_curve_dialog  # DIFF-003-006
        if label == "Hue (per color)":  # DIFF-003-003
            return lambda: self._open_hsl_dialog("h")  # DIFF-003-003
        if label == "Saturation (per color)":  # DIFF-003-003
            return lambda: self._open_hsl_dialog("s")  # DIFF-003-003
        if label == "Luminance (per color)":  # DIFF-003-003
            return lambda: self._open_hsl_dialog("l")  # DIFF-003-003
        if label in {"Shadows Color", "Midtones Color", "Highlights Color", "Balance", "Split Toning (Highlight Hue/Sat, Shadow Hue/Sat)"}:  # DIFF-003-006
            return self._open_color_grading_dialog  # DIFF-003-006
        if label in {"Levels (Input/Output)", "RGB Levels"}:  # DIFF-003-006
            return lambda: self._open_levels_dialog(mode="global")  # DIFF-003-006
        if label == "Individual Channel Levels":  # DIFF-003-006
            return lambda: self._open_levels_dialog(mode="channels")  # DIFF-003-006
        if label == "Crop":  # DIFF-003-007
            return self._open_crop_dialog  # DIFF-003-007
        if label == "Rotate":  # DIFF-003-007
            return self._open_rotate_dialog  # DIFF-003-007
        if label == "Straighten":  # DIFF-003-007
            return self._open_straighten_dialog  # DIFF-003-007
        if label == "Perspective (Vertical/Horizontal)":  # DIFF-003-007
            return self._open_perspective_dialog  # DIFF-003-007
        if label == "Distort / Warp":  # DIFF-003-007
            return self._open_distort_dialog  # DIFF-003-007
        if label == "Scale":  # DIFF-003-007
            return self._open_scale_dialog  # DIFF-003-007
        if label == "Flip Horizontal / Vertical":  # DIFF-003-007
            return self._open_flip_dialog  # DIFF-003-007
        return None  # DIFF-003-006

    def _open_numeric_dialog(self, title: str, fields: list[dict], values: dict, on_apply) -> None:  # DIFF-003-006
        dialog = QDialog(self)  # DIFF-003-006
        dialog.setWindowTitle(title)  # DIFF-003-006
        form = QFormLayout(dialog)  # DIFF-003-006
        widgets = {}  # DIFF-003-006
        for field in fields:  # DIFF-003-006
            key = field["key"]  # DIFF-003-006
            is_float = field.get("float", False)  # DIFF-003-006
            if is_float:  # DIFF-003-006
                widget = QDoubleSpinBox()  # DIFF-003-006
                widget.setDecimals(field.get("decimals", 2))  # DIFF-003-006
                widget.setSingleStep(field.get("step", 0.1))  # DIFF-003-006
            else:  # DIFF-003-006
                widget = QSpinBox()  # DIFF-003-006
                widget.setSingleStep(field.get("step", 1))  # DIFF-003-006
            widget.setRange(field.get("min", -100), field.get("max", 100))  # DIFF-003-006
            widget.setValue(values.get(key, field.get("default", 0)))  # DIFF-003-006
            form.addRow(field.get("label", key), widget)  # DIFF-003-006
            widgets[key] = widget  # DIFF-003-006
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # DIFF-003-006
        buttons.accepted.connect(dialog.accept)  # DIFF-003-006
        buttons.rejected.connect(dialog.reject)  # DIFF-003-006
        form.addRow(buttons)  # DIFF-003-006
        if dialog.exec() == QDialog.Accepted:  # DIFF-003-006
            updated = {}  # DIFF-003-006
            for key, widget in widgets.items():  # DIFF-003-006
                updated[key] = widget.value()  # DIFF-003-006
            on_apply(updated)  # DIFF-003-006
            self._schedule_edit_preview()  # DIFF-003-006
            self._schedule_edit_state_commit()  # DIFF-003-006

    def _open_tone_curve_dialog(self) -> None:  # DIFF-003-006
        curve = self._advanced_settings["curves"]["rgb"]  # DIFF-003-006
        fields = [  # DIFF-003-006
            {"key": "shadows", "label": "Shadows", "min": -100, "max": 100, "step": 1},  # DIFF-003-006
            {"key": "midtones", "label": "Midtones", "min": -100, "max": 100, "step": 1},  # DIFF-003-006
            {"key": "highlights", "label": "Highlights", "min": -100, "max": 100, "step": 1},  # DIFF-003-006
        ]  # DIFF-003-006
        self._open_numeric_dialog(  # DIFF-003-006
            "Tone Curve (RGB)", fields, curve, lambda vals: curve.update(vals)  # DIFF-003-006
        )  # DIFF-003-006

    def _open_channel_curve_dialog(self) -> None:  # DIFF-003-006
        for channel in ("r", "g", "b"):  # DIFF-003-006
            curve = self._advanced_settings["curves"][channel]  # DIFF-003-006
            fields = [  # DIFF-003-006
                {"key": "shadows", "label": f"{channel.upper()} Shadows", "min": -100, "max": 100, "step": 1},  # DIFF-003-006
                {"key": "midtones", "label": f"{channel.upper()} Midtones", "min": -100, "max": 100, "step": 1},  # DIFF-003-006
                {"key": "highlights", "label": f"{channel.upper()} Highlights", "min": -100, "max": 100, "step": 1},  # DIFF-003-006
            ]  # DIFF-003-006
            self._open_numeric_dialog(  # DIFF-003-006
                f"Channel Curve ({channel.upper()})",  # DIFF-003-006
                fields,  # DIFF-003-006
                curve,  # DIFF-003-006
                lambda vals, target=curve: target.update(vals),  # DIFF-003-006
            )  # DIFF-003-006

    def _open_hsl_dialog(self, mode: str) -> None:  # DIFF-003-003
        dialog = QDialog(self)  # DIFF-003-003
        dialog.setWindowTitle(f"HSL {mode.upper()} (Per Color)")  # DIFF-003-003
        form = QFormLayout(dialog)  # DIFF-003-003
        widgets = {}  # DIFF-003-003
        for band in HSL_COLOR_BANDS:  # DIFF-003-003
            widget = QSpinBox()  # DIFF-003-003
            if mode == "h":  # DIFF-003-003
                widget.setRange(-180, 180)  # DIFF-003-003
            else:  # DIFF-003-003
                widget.setRange(-100, 100)  # DIFF-003-003
            widget.setSingleStep(1)  # DIFF-003-003
            widget.setValue(self._advanced_settings["hsl"][band][mode])  # DIFF-003-003
            form.addRow(band.title(), widget)  # DIFF-003-003
            widgets[band] = widget  # DIFF-003-003
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # DIFF-003-003
        buttons.accepted.connect(dialog.accept)  # DIFF-003-003
        buttons.rejected.connect(dialog.reject)  # DIFF-003-003
        form.addRow(buttons)  # DIFF-003-003
        if dialog.exec() == QDialog.Accepted:  # DIFF-003-003
            for band, widget in widgets.items():  # DIFF-003-003
                self._advanced_settings["hsl"][band][mode] = widget.value()  # DIFF-003-003
            self._schedule_edit_preview()  # DIFF-003-003
            self._schedule_edit_state_commit()  # DIFF-003-003

    def _open_color_grading_dialog(self) -> None:  # DIFF-003-006
        settings = self._advanced_settings["color_grading"]  # DIFF-003-006
        dialog = QDialog(self)  # DIFF-003-006
        dialog.setWindowTitle("Color Grading")  # DIFF-003-006
        form = QFormLayout(dialog)  # DIFF-003-006

        color_buttons = {}  # DIFF-003-006
        strength_fields = {}  # DIFF-003-006
        for label, key in (("Shadows", "shadows"), ("Midtones", "midtones"), ("Highlights", "highlights")):  # DIFF-003-006
            color_btn = QPushButton(f"{label} Color")  # DIFF-003-006
            color = settings[f"{key}_color"]  # DIFF-003-006
            color_btn.setStyleSheet(f"background-color: rgb({color[0]}, {color[1]}, {color[2]});")  # DIFF-003-006
            def make_pick(btn=color_btn, k=key):  # DIFF-003-006
                selected = QColorDialog.getColor(QColor(*settings[f"{k}_color"]), self)  # DIFF-003-006
                if selected.isValid():  # DIFF-003-006
                    settings[f"{k}_color"] = (selected.red(), selected.green(), selected.blue())  # DIFF-003-006
                    btn.setStyleSheet(f"background-color: rgb({selected.red()}, {selected.green()}, {selected.blue()});")  # DIFF-003-006
            color_btn.clicked.connect(make_pick)  # DIFF-003-006
            strength = QSpinBox()  # DIFF-003-006
            strength.setRange(0, 100)  # DIFF-003-006
            strength.setValue(settings[f"{key}_strength"])  # DIFF-003-006
            strength_fields[key] = strength  # DIFF-003-006
            row = QHBoxLayout()  # DIFF-003-006
            row.addWidget(color_btn)  # DIFF-003-006
            row.addWidget(QLabel("Strength"))  # DIFF-003-006
            row.addWidget(strength)  # DIFF-003-006
            row.addStretch(1)  # DIFF-003-006
            form.addRow(label, row)  # DIFF-003-006
            color_buttons[key] = color_btn  # DIFF-003-006

        balance = QSpinBox()  # DIFF-003-006
        balance.setRange(-100, 100)  # DIFF-003-006
        balance.setValue(settings["balance"])  # DIFF-003-006
        form.addRow("Balance", balance)  # DIFF-003-006

        split_highlight_h = QSpinBox()  # DIFF-003-006
        split_highlight_h.setRange(0, 360)  # DIFF-003-006
        split_highlight_h.setValue(settings["split_highlight_h"])  # DIFF-003-006
        split_highlight_s = QSpinBox()  # DIFF-003-006
        split_highlight_s.setRange(0, 100)  # DIFF-003-006
        split_highlight_s.setValue(settings["split_highlight_s"])  # DIFF-003-006
        split_shadow_h = QSpinBox()  # DIFF-003-006
        split_shadow_h.setRange(0, 360)  # DIFF-003-006
        split_shadow_h.setValue(settings["split_shadow_h"])  # DIFF-003-006
        split_shadow_s = QSpinBox()  # DIFF-003-006
        split_shadow_s.setRange(0, 100)  # DIFF-003-006
        split_shadow_s.setValue(settings["split_shadow_s"])  # DIFF-003-006
        split_row = QHBoxLayout()  # DIFF-003-006
        split_row.addWidget(QLabel("Highlight Hue"))  # DIFF-003-006
        split_row.addWidget(split_highlight_h)  # DIFF-003-006
        split_row.addWidget(QLabel("Highlight Sat"))  # DIFF-003-006
        split_row.addWidget(split_highlight_s)  # DIFF-003-006
        split_row.addWidget(QLabel("Shadow Hue"))  # DIFF-003-006
        split_row.addWidget(split_shadow_h)  # DIFF-003-006
        split_row.addWidget(QLabel("Shadow Sat"))  # DIFF-003-006
        split_row.addWidget(split_shadow_s)  # DIFF-003-006
        form.addRow("Split Toning", split_row)  # DIFF-003-006

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # DIFF-003-006
        buttons.accepted.connect(dialog.accept)  # DIFF-003-006
        buttons.rejected.connect(dialog.reject)  # DIFF-003-006
        form.addRow(buttons)  # DIFF-003-006
        if dialog.exec() == QDialog.Accepted:  # DIFF-003-006
            settings["shadows_strength"] = strength_fields["shadows"].value()  # DIFF-003-006
            settings["midtones_strength"] = strength_fields["midtones"].value()  # DIFF-003-006
            settings["highlights_strength"] = strength_fields["highlights"].value()  # DIFF-003-006
            settings["balance"] = balance.value()  # DIFF-003-006
            settings["split_highlight_h"] = split_highlight_h.value()  # DIFF-003-006
            settings["split_highlight_s"] = split_highlight_s.value()  # DIFF-003-006
            settings["split_shadow_h"] = split_shadow_h.value()  # DIFF-003-006
            settings["split_shadow_s"] = split_shadow_s.value()  # DIFF-003-006
            self._schedule_edit_preview()  # DIFF-003-006
            self._schedule_edit_state_commit()  # DIFF-003-006

    def _open_levels_dialog(self, mode: str) -> None:  # DIFF-003-006
        dialog = QDialog(self)  # DIFF-003-006
        dialog.setWindowTitle("Levels")  # DIFF-003-006
        layout = QVBoxLayout(dialog)  # DIFF-003-006
        entries = {}  # DIFF-003-006

        def add_level_group(title: str, target: dict):  # DIFF-003-006
            group = QGroupBox(title)  # DIFF-003-006
            form = QFormLayout(group)  # DIFF-003-006
            in_black = QSpinBox()  # DIFF-003-006
            in_black.setRange(0, 255)  # DIFF-003-006
            in_black.setValue(target["in_black"])  # DIFF-003-006
            in_gamma = QDoubleSpinBox()  # DIFF-003-006
            in_gamma.setRange(0.1, 5.0)  # DIFF-003-006
            in_gamma.setDecimals(2)  # DIFF-003-006
            in_gamma.setSingleStep(0.05)  # DIFF-003-006
            in_gamma.setValue(target["in_gamma"])  # DIFF-003-006
            in_white = QSpinBox()  # DIFF-003-006
            in_white.setRange(0, 255)  # DIFF-003-006
            in_white.setValue(target["in_white"])  # DIFF-003-006
            out_black = QSpinBox()  # DIFF-003-006
            out_black.setRange(0, 255)  # DIFF-003-006
            out_black.setValue(target["out_black"])  # DIFF-003-006
            out_white = QSpinBox()  # DIFF-003-006
            out_white.setRange(0, 255)  # DIFF-003-006
            out_white.setValue(target["out_white"])  # DIFF-003-006
            form.addRow("Input Black", in_black)  # DIFF-003-006
            form.addRow("Input Gamma", in_gamma)  # DIFF-003-006
            form.addRow("Input White", in_white)  # DIFF-003-006
            form.addRow("Output Black", out_black)  # DIFF-003-006
            form.addRow("Output White", out_white)  # DIFF-003-006
            layout.addWidget(group)  # DIFF-003-006
            entries[title] = {  # DIFF-003-006
                "in_black": in_black,  # DIFF-003-006
                "in_gamma": in_gamma,  # DIFF-003-006
                "in_white": in_white,  # DIFF-003-006
                "out_black": out_black,  # DIFF-003-006
                "out_white": out_white,  # DIFF-003-006
                "target": target,  # DIFF-003-006
            }  # DIFF-003-006

        if mode == "global":  # DIFF-003-006
            add_level_group("Global", self._advanced_settings["levels"]["global"])  # DIFF-003-006
        else:  # DIFF-003-006
            for channel in ("r", "g", "b"):  # DIFF-003-006
                add_level_group(channel.upper(), self._advanced_settings["levels"]["channels"][channel])  # DIFF-003-006

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # DIFF-003-006
        buttons.accepted.connect(dialog.accept)  # DIFF-003-006
        buttons.rejected.connect(dialog.reject)  # DIFF-003-006
        layout.addWidget(buttons)  # DIFF-003-006
        if dialog.exec() == QDialog.Accepted:  # DIFF-003-006
            for group in entries.values():  # DIFF-003-006
                target = group["target"]  # DIFF-003-006
                target["in_black"] = group["in_black"].value()  # DIFF-003-006
                target["in_gamma"] = group["in_gamma"].value()  # DIFF-003-006
                target["in_white"] = group["in_white"].value()  # DIFF-003-006
                target["out_black"] = group["out_black"].value()  # DIFF-003-006
                target["out_white"] = group["out_white"].value()  # DIFF-003-006
            self._schedule_edit_preview()  # DIFF-003-006
            self._schedule_edit_state_commit()  # DIFF-003-006

    def _open_crop_dialog(self) -> None:  # DIFF-003-007
        crop = self._geometry_settings["crop"]  # DIFF-003-007
        fields = [  # DIFF-003-007
            {"key": "left", "label": "Left (%)", "min": 0, "max": 90, "step": 1},  # DIFF-003-007
            {"key": "top", "label": "Top (%)", "min": 0, "max": 90, "step": 1},  # DIFF-003-007
            {"key": "right", "label": "Right (%)", "min": 0, "max": 90, "step": 1},  # DIFF-003-007
            {"key": "bottom", "label": "Bottom (%)", "min": 0, "max": 90, "step": 1},  # DIFF-003-007
        ]  # DIFF-003-007
        self._open_numeric_dialog("Crop", fields, crop, lambda vals: crop.update(vals))  # DIFF-003-007

    def _open_rotate_dialog(self) -> None:  # DIFF-003-007
        fields = [  # DIFF-003-007
            {"key": "rotate", "label": "Rotate (degrees)", "min": -180, "max": 180, "step": 1, "float": True, "decimals": 1},  # DIFF-003-007
        ]  # DIFF-003-007
        self._open_numeric_dialog(  # DIFF-003-007
            "Rotate", fields, self._geometry_settings, lambda vals: self._geometry_settings.update(vals)  # DIFF-003-007
        )  # DIFF-003-007

    def _open_straighten_dialog(self) -> None:  # DIFF-003-007
        fields = [  # DIFF-003-007
            {"key": "straighten", "label": "Straighten (degrees)", "min": -45, "max": 45, "step": 0.5, "float": True, "decimals": 1},  # DIFF-003-007
        ]  # DIFF-003-007
        self._open_numeric_dialog(  # DIFF-003-007
            "Straighten", fields, self._geometry_settings, lambda vals: self._geometry_settings.update(vals)  # DIFF-003-007
        )  # DIFF-003-007

    def _open_perspective_dialog(self) -> None:  # DIFF-003-007
        fields = [  # DIFF-003-007
            {"key": "perspective_h", "label": "Horizontal", "min": -50, "max": 50, "step": 1},  # DIFF-003-007
            {"key": "perspective_v", "label": "Vertical", "min": -50, "max": 50, "step": 1},  # DIFF-003-007
        ]  # DIFF-003-007
        self._open_numeric_dialog(  # DIFF-003-007
            "Perspective", fields, self._geometry_settings, lambda vals: self._geometry_settings.update(vals)  # DIFF-003-007
        )  # DIFF-003-007

    def _open_distort_dialog(self) -> None:  # DIFF-003-007
        fields = [  # DIFF-003-007
            {"key": "distort_h", "label": "Horizontal", "min": -50, "max": 50, "step": 1},  # DIFF-003-007
            {"key": "distort_v", "label": "Vertical", "min": -50, "max": 50, "step": 1},  # DIFF-003-007
        ]  # DIFF-003-007
        self._open_numeric_dialog(  # DIFF-003-007
            "Distort / Warp", fields, self._geometry_settings, lambda vals: self._geometry_settings.update(vals)  # DIFF-003-007
        )  # DIFF-003-007

    def _open_scale_dialog(self) -> None:  # DIFF-003-007
        fields = [  # DIFF-003-007
            {"key": "scale_x", "label": "Scale X (%)", "min": 10, "max": 300, "step": 1},  # DIFF-003-007
            {"key": "scale_y", "label": "Scale Y (%)", "min": 10, "max": 300, "step": 1},  # DIFF-003-007
        ]  # DIFF-003-007
        self._open_numeric_dialog(  # DIFF-003-007
            "Scale", fields, self._geometry_settings, lambda vals: self._geometry_settings.update(vals)  # DIFF-003-007
        )  # DIFF-003-007

    def _open_flip_dialog(self) -> None:  # DIFF-003-007
        dialog = QDialog(self)  # DIFF-003-007
        dialog.setWindowTitle("Flip")  # DIFF-003-007
        layout = QVBoxLayout(dialog)  # DIFF-003-007
        flip_h = QCheckBox("Flip Horizontal")  # DIFF-003-007
        flip_h.setChecked(self._geometry_settings["flip_h"])  # DIFF-003-007
        flip_v = QCheckBox("Flip Vertical")  # DIFF-003-007
        flip_v.setChecked(self._geometry_settings["flip_v"])  # DIFF-003-007
        layout.addWidget(flip_h)  # DIFF-003-007
        layout.addWidget(flip_v)  # DIFF-003-007
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # DIFF-003-007
        buttons.accepted.connect(dialog.accept)  # DIFF-003-007
        buttons.rejected.connect(dialog.reject)  # DIFF-003-007
        layout.addWidget(buttons)  # DIFF-003-007
        if dialog.exec() == QDialog.Accepted:  # DIFF-003-007
            self._geometry_settings["flip_h"] = flip_h.isChecked()  # DIFF-003-007
            self._geometry_settings["flip_v"] = flip_v.isChecked()  # DIFF-003-007
            self._schedule_edit_preview()  # DIFF-003-007
            self._schedule_edit_state_commit()  # DIFF-003-007

    def _build_brush_controls(self, parent_layout: QVBoxLayout) -> None:
        brush_row = QHBoxLayout()
        brush_row.addWidget(QLabel("Brush"))
        self.brush_toggle = QPushButton("Enable")
        self.brush_toggle.setCheckable(True)
        self._standard_button(self.brush_toggle)
        brush_row.addWidget(self.brush_toggle)
        brush_row.addStretch(1)
        parent_layout.addLayout(brush_row)
        self.brush_toggle.toggled.connect(self._on_brush_toggled)  # DIFF-003-007

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Brush Size"))
        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(1, 200)
        self.brush_size_slider.setValue(40)
        self.brush_size_slider.setSingleStep(1)
        self.brush_size_value = QLabel("40 px")
        self.brush_size_value.setMinimumWidth(56)
        self.brush_preview = QLabel()
        self._set_brush_preview_size(40)
        size_row.addWidget(self.brush_size_slider)
        size_row.addWidget(self.brush_size_value)
        size_row.addWidget(self.brush_preview)
        size_row.addStretch(1)
        parent_layout.addLayout(size_row)

        self.brush_size_slider.valueChanged.connect(self._on_brush_size_changed)

    def _set_brush_preview_size(self, size: int) -> None:
        preview_size = max(6, min(60, size))
        radius = preview_size // 2
        self.brush_preview.setFixedSize(preview_size, preview_size)
        self.brush_preview.setStyleSheet(
            f"border: 1px solid #666; border-radius: {radius}px;"
        )

    def _on_brush_size_changed(self, value: int) -> None:  # DIFF-003-007
        self.brush_size_value.setText(f"{value} px")  # DIFF-003-007
        self._set_brush_preview_size(value)  # DIFF-003-007
        self._schedule_edit_preview()  # DIFF-003-007
        self._schedule_edit_state_commit()  # DIFF-003-007

    def _on_brush_toggled(self, enabled: bool) -> None:  # DIFF-003-007
        if enabled and self._brush_mask is None and self._edit_preview_base:  # DIFF-003-007
            self._brush_mask = QImage(  # DIFF-003-007
                self._edit_preview_base.size(), QImage.Format_Grayscale8  # DIFF-003-007
            )  # DIFF-003-007
            self._brush_mask.fill(0)  # DIFF-003-007
        self._schedule_edit_preview()  # DIFF-003-007
        self._schedule_edit_state_commit()  # DIFF-003-007

    def eventFilter(self, watched, event):  # DIFF-003-007
        if hasattr(self, "edit_view") and watched is self.edit_view.viewport():  # DIFF-003-007
            if not self._edit_preview_base:  # DIFF-003-007
                return super().eventFilter(watched, event)  # DIFF-003-007
            if not hasattr(self, "brush_toggle") or not self.brush_toggle.isChecked():  # DIFF-003-007
                return super().eventFilter(watched, event)  # DIFF-003-007
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:  # DIFF-003-007
                self._brush_painting = True  # DIFF-003-007
                self._paint_brush_at(event.position().toPoint())  # DIFF-003-007
                return True  # DIFF-003-007
            if event.type() == QEvent.MouseMove and self._brush_painting and event.buttons() & Qt.LeftButton:  # DIFF-003-007
                self._paint_brush_at(event.position().toPoint())  # DIFF-003-007
                return True  # DIFF-003-007
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:  # DIFF-003-007
                self._brush_painting = False  # DIFF-003-007
                self._schedule_edit_state_commit()  # DIFF-003-007
                return True  # DIFF-003-007
        return super().eventFilter(watched, event)  # DIFF-003-007

    def _paint_brush_at(self, pos) -> None:  # DIFF-003-007
        if not self._edit_preview_base:  # DIFF-003-007
            return  # DIFF-003-007
        if self._brush_mask is None:  # DIFF-003-007
            self._brush_mask = QImage(  # DIFF-003-007
                self._edit_preview_base.size(), QImage.Format_Grayscale8  # DIFF-003-007
            )  # DIFF-003-007
            self._brush_mask.fill(0)  # DIFF-003-007
        scene_pos = self.edit_view.mapToScene(pos)  # DIFF-003-007
        x = int(scene_pos.x())  # DIFF-003-007
        y = int(scene_pos.y())  # DIFF-003-007
        if x < 0 or y < 0 or x >= self._edit_preview_base.width() or y >= self._edit_preview_base.height():  # DIFF-003-007
            return  # DIFF-003-007
        size = self.brush_size_slider.value() if hasattr(self, "brush_size_slider") else 40  # DIFF-003-007
        radius = max(1, size // 2)  # DIFF-003-007
        painter = QPainter(self._brush_mask)  # DIFF-003-007
        painter.setRenderHint(QPainter.Antialiasing, True)  # DIFF-003-007
        painter.setPen(Qt.NoPen)  # DIFF-003-007
        painter.setBrush(QColor(255, 255, 255))  # DIFF-003-007
        painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)  # DIFF-003-007
        painter.end()  # DIFF-003-007
        self._brush_dirty = True  # DIFF-003-007
        self._schedule_edit_preview()  # DIFF-003-007

    def _register_adjustment_slider(
        self,
        key: str,
        slider: QSlider,
        value_label: QLabel,
        config: dict,
    ) -> None:
        scale = config.get("scale", 1)
        suffix = config.get("suffix", "")
        default = config.get("default", 0)
        self._adjustment_sliders[key] = slider
        self._adjustment_value_labels[key] = value_label
        self._adjustment_scales[key] = scale
        self._adjustment_suffixes[key] = suffix
        self._adjustment_defaults[key] = int(round(default * scale))
        if key == "brightness":
            self.brightness_slider = slider
            self.brightness_value = value_label
        elif key == "contrast":
            self.contrast_slider = slider
            self.contrast_value = value_label
        elif key == "saturation":
            self.saturation_slider = slider
            self.saturation_value = value_label
        self._wire_adjustment_slider(slider)

    def _build_adjustment_row(
        self,
        label: str,
        parent_layout: QVBoxLayout,
        min_val: float = -100,
        max_val: float = 100,
        step: float = 1,
        default: float = 0,
        scale: int = 1,
        suffix: str = "",
    ) -> tuple[QSlider, QLabel]:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        slider = QSlider(Qt.Horizontal)
        slider.setRange(int(round(min_val * scale)), int(round(max_val * scale)))
        slider.setValue(int(round(default * scale)))
        slider.setSingleStep(int(round(step * scale)))
        value_label = QLabel("")
        value_label.setMinimumWidth(56)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._set_adjustment_value_label(value_label, slider.value(), scale, suffix)
        slider.valueChanged.connect(
            lambda val, lbl=value_label, sc=scale, suf=suffix: self._set_adjustment_value_label(
                lbl, val, sc, suf
            )
        )
        row.addWidget(slider)
        row.addWidget(value_label)
        row.addStretch(1)
        parent_layout.addLayout(row)
        return slider, value_label

    def _set_adjustment_value_label(self, label: QLabel, raw: int, scale: int, suffix: str) -> None:
        if scale == 1:
            text = str(raw)
        else:
            decimals = 0
            if scale in (10, 100, 1000):
                decimals = len(str(scale)) - 1
            value = raw / scale
            text = f"{value:.{decimals}f}".rstrip("0").rstrip(".")
        label.setText(f"{text}{suffix}")

    def _wire_adjustment_slider(self, slider: QSlider) -> None:
        slider.valueChanged.connect(lambda _val: self._schedule_edit_preview())  # DIFF-003-001
        slider.valueChanged.connect(lambda _val: self._schedule_edit_state_commit())  # DIFF-003-001

    def _schedule_edit_preview(self) -> None:  # DIFF-003-001
        if not self._edit_preview_base:  # DIFF-003-001
            return  # DIFF-003-001
        self._edit_preview_timer.start(150)  # DIFF-003-001

    def _schedule_edit_state_commit(self) -> None:  # DIFF-003-001
        if self._suppress_state_commit:  # DIFF-003-001
            return  # DIFF-003-001
        self._edit_state_timer.start(300)  # DIFF-003-001

    def _commit_edit_state(self) -> None:  # DIFF-003-001
        if self._suppress_state_commit:  # DIFF-003-001
            return  # DIFF-003-001
        if not self._edit_preview_base:  # DIFF-003-001
            return  # DIFF-003-001
        snapshot = self._capture_edit_state()  # DIFF-003-001
        if self._current_state is not None:  # DIFF-003-001
            self._undo_stack.append(self._current_state)  # DIFF-003-001
            if len(self._undo_stack) > self._history_limit:  # DIFF-003-001
                self._undo_stack.pop(0)  # DIFF-003-001
        self._current_state = snapshot  # DIFF-003-001
        self._redo_stack.clear()  # DIFF-003-001
        self._brush_dirty = False  # DIFF-003-007

    def _init_edit_shortcuts(self) -> None:  # DIFF-003-001
        self._undo_shortcut = QShortcut(QKeySequence.Undo, self)  # DIFF-003-001
        self._undo_shortcut.activated.connect(self._undo_edit)  # DIFF-003-001
        self._redo_shortcut = QShortcut(QKeySequence.Redo, self)  # DIFF-003-001
        self._redo_shortcut.activated.connect(self._redo_edit)  # DIFF-003-001

    def _undo_edit(self) -> None:  # DIFF-003-001
        if not self._undo_stack:  # DIFF-003-001
            return  # DIFF-003-001
        if self._current_state is not None:  # DIFF-003-001
            self._redo_stack.append(self._current_state)  # DIFF-003-001
        state = self._undo_stack.pop()  # DIFF-003-001
        self._apply_edit_state(state)  # DIFF-003-001

    def _redo_edit(self) -> None:  # DIFF-003-001
        if not self._redo_stack:  # DIFF-003-001
            return  # DIFF-003-001
        if self._current_state is not None:  # DIFF-003-001
            self._undo_stack.append(self._current_state)  # DIFF-003-001
        state = self._redo_stack.pop()  # DIFF-003-001
        self._apply_edit_state(state)  # DIFF-003-001

    def _capture_edit_state(self) -> dict:  # DIFF-003-001
        sliders = {key: slider.value() for key, slider in self._adjustment_sliders.items()}  # DIFF-003-001
        brush_enabled = False  # DIFF-003-007
        brush_size = 40  # DIFF-003-007
        if hasattr(self, "brush_toggle"):  # DIFF-003-007
            brush_enabled = self.brush_toggle.isChecked()  # DIFF-003-007
        if hasattr(self, "brush_size_slider"):  # DIFF-003-007
            brush_size = self.brush_size_slider.value()  # DIFF-003-007
        mask_copy = self._brush_mask.copy() if self._brush_mask else None  # DIFF-003-007
        return {  # DIFF-003-001
            "sliders": sliders,  # DIFF-003-001
            "advanced": copy.deepcopy(self._advanced_settings),  # DIFF-003-001
            "geometry": copy.deepcopy(self._geometry_settings),  # DIFF-003-001
            "brush_enabled": brush_enabled,  # DIFF-003-001
            "brush_size": brush_size,  # DIFF-003-001
            "brush_mask": mask_copy,  # DIFF-003-001
        }  # DIFF-003-001

    def _apply_edit_state(self, state: dict) -> None:  # DIFF-003-001
        self._suppress_state_commit = True  # DIFF-003-001
        for key, slider in self._adjustment_sliders.items():  # DIFF-003-001
            if key not in state.get("sliders", {}):  # DIFF-003-001
                continue  # DIFF-003-001
            slider.blockSignals(True)  # DIFF-003-001
            slider.setValue(state["sliders"][key])  # DIFF-003-001
            slider.blockSignals(False)  # DIFF-003-001
            label = self._adjustment_value_labels.get(key)  # DIFF-003-001
            if label:  # DIFF-003-001
                self._set_adjustment_value_label(  # DIFF-003-001
                    label,  # DIFF-003-001
                    slider.value(),  # DIFF-003-001
                    self._adjustment_scales.get(key, 1),  # DIFF-003-001
                    self._adjustment_suffixes.get(key, ""),  # DIFF-003-001
                )  # DIFF-003-001
        self._advanced_settings = copy.deepcopy(state.get("advanced", {}))  # DIFF-003-006
        self._geometry_settings = copy.deepcopy(state.get("geometry", {}))  # DIFF-003-007
        if hasattr(self, "brush_toggle"):  # DIFF-003-007
            self.brush_toggle.setChecked(state.get("brush_enabled", False))  # DIFF-003-007
        if hasattr(self, "brush_size_slider"):  # DIFF-003-007
            self.brush_size_slider.setValue(state.get("brush_size", 40))  # DIFF-003-007
        self._brush_mask = state.get("brush_mask")  # DIFF-003-007
        self._brush_dirty = False  # DIFF-003-007
        self._current_state = self._capture_edit_state()  # DIFF-003-001
        self._suppress_state_commit = False  # DIFF-003-001
        self._schedule_edit_preview()  # DIFF-003-001

    def _update_edit_preview(self) -> None:  # DIFF-003-001
        if not self._edit_preview_base:  # DIFF-003-001
            return  # DIFF-003-001
        adjusted = self._apply_edit_pipeline(self._edit_preview_base, preview=True)  # DIFF-003-001
        self._edit_working_preview = adjusted  # DIFF-003-001
        self.edit_view.set_image_data(adjusted, preserve_zoom=True)  # DIFF-003-001

    def _reset_adjustments(self, update_preview: bool = True) -> None:  # DIFF-003-001
        if not hasattr(self, "_adjustment_sliders"):  # DIFF-003-001
            return  # DIFF-003-001
        self._suppress_state_commit = True  # DIFF-003-001
        for key, slider in self._adjustment_sliders.items():  # DIFF-003-001
            slider.blockSignals(True)  # DIFF-003-001
            slider.setValue(self._adjustment_defaults.get(key, 0))  # DIFF-003-001
            slider.blockSignals(False)  # DIFF-003-001
            label = self._adjustment_value_labels.get(key)  # DIFF-003-001
            if label:  # DIFF-003-001
                self._set_adjustment_value_label(  # DIFF-003-001
                    label,  # DIFF-003-001
                    slider.value(),  # DIFF-003-001
                    self._adjustment_scales.get(key, 1),  # DIFF-003-001
                    self._adjustment_suffixes.get(key, ""),  # DIFF-003-001
                )  # DIFF-003-001
        self._advanced_settings = self._default_advanced_settings()  # DIFF-003-006
        self._geometry_settings = self._default_geometry_settings()  # DIFF-003-007
        if hasattr(self, "brush_toggle"):  # DIFF-003-007
            self.brush_toggle.setChecked(False)  # DIFF-003-007
        if hasattr(self, "brush_size_slider"):  # DIFF-003-007
            self.brush_size_slider.setValue(40)  # DIFF-003-007
        self._brush_mask = None  # DIFF-003-007
        self._brush_dirty = False  # DIFF-003-007
        self._undo_stack.clear()  # DIFF-003-001
        self._redo_stack.clear()  # DIFF-003-001
        self._current_state = self._capture_edit_state()  # DIFF-003-001
        self._suppress_state_commit = False  # DIFF-003-001
        if update_preview and self._edit_preview_base:  # DIFF-003-001
            self._schedule_edit_preview()  # DIFF-003-001

    def _save_adjusted_copy(self) -> None:  # DIFF-003-008
        if not self._edit_original or not self._edit_current_path:  # DIFF-003-008
            QMessageBox.information(self, "No Image", "Select an image to adjust.")  # DIFF-003-008
            return  # DIFF-003-008
        adjusted = self._apply_edit_pipeline(self._edit_original, preview=False)  # DIFF-003-001
        output_path = self._resolve_output_path(self._edit_current_path, "_edited")  # DIFF-003-008
        if not output_path:  # DIFF-003-008
            return  # DIFF-003-008
        if adjusted.save(output_path):  # DIFF-003-008
            QMessageBox.information(self, "Saved", f"Adjusted copy saved to:\n{output_path}")  # DIFF-003-008
        else:  # DIFF-003-008
            QMessageBox.warning(self, "Save Failed", "Unable to save the adjusted image.")  # DIFF-003-008

    def _save_upscaled_copy(self) -> None:  # DIFF-003-008
        if not self._edit_original or not self._edit_current_path:  # DIFF-003-008
            QMessageBox.information(self, "No Image", "Select an image to upscale.")  # DIFF-003-008
            return  # DIFF-003-008
        factor_text = self.upscale_combo.currentText().replace("x", "")  # DIFF-003-008
        try:  # DIFF-003-008
            factor = int(factor_text)  # DIFF-003-008
        except ValueError:  # DIFF-003-008
            factor = 2  # DIFF-003-008
        base = self._apply_edit_pipeline(self._edit_original, preview=False)  # DIFF-003-001
        width = base.width() * factor  # DIFF-003-008
        height = base.height() * factor  # DIFF-003-008
        scaled = base.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)  # DIFF-003-008
        output_path = self._resolve_output_path(self._edit_current_path, f"_upscale_{factor}x")  # DIFF-003-008
        if not output_path:  # DIFF-003-008
            return  # DIFF-003-008
        if scaled.save(output_path):  # DIFF-003-008
            QMessageBox.information(self, "Saved", f"Upscaled copy saved to:\n{output_path}")  # DIFF-003-008
        else:  # DIFF-003-008
            QMessageBox.warning(self, "Save Failed", "Unable to save the upscaled image.")  # DIFF-003-008

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

    def _resolve_output_path(self, original_path: str, suffix: str) -> str:  # DIFF-003-008
        keep_original = True  # DIFF-003-008
        if hasattr(self, "keep_original_checkbox"):  # DIFF-003-008
            keep_original = self.keep_original_checkbox.isChecked()  # DIFF-003-008
        if keep_original:  # DIFF-003-008
            return self._suggest_output_path(original_path, suffix)  # DIFF-003-008
        reply = QMessageBox.question(  # DIFF-003-008
            self,  # DIFF-003-008
            "Overwrite Original?",  # DIFF-003-008
            "This will overwrite the original file. Continue?",  # DIFF-003-008
            QMessageBox.Yes | QMessageBox.No,  # DIFF-003-008
            QMessageBox.No,  # DIFF-003-008
        )  # DIFF-003-008
        if reply != QMessageBox.Yes:  # DIFF-003-008
            return ""  # DIFF-003-008
        return original_path  # DIFF-003-008

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

    def _default_advanced_settings(self) -> dict:  # DIFF-003-006
        hsl = {band: {"h": 0, "s": 0, "l": 0} for band in HSL_COLOR_BANDS}  # DIFF-003-003
        levels = {  # DIFF-003-006
            "global": {"in_black": 0, "in_gamma": 1.0, "in_white": 255, "out_black": 0, "out_white": 255},
            "channels": {
                "r": {"in_black": 0, "in_gamma": 1.0, "in_white": 255, "out_black": 0, "out_white": 255},
                "g": {"in_black": 0, "in_gamma": 1.0, "in_white": 255, "out_black": 0, "out_white": 255},
                "b": {"in_black": 0, "in_gamma": 1.0, "in_white": 255, "out_black": 0, "out_white": 255},
            },
        }
        return {
            "curves": {
                "rgb": {"shadows": 0, "midtones": 0, "highlights": 0},
                "r": {"shadows": 0, "midtones": 0, "highlights": 0},
                "g": {"shadows": 0, "midtones": 0, "highlights": 0},
                "b": {"shadows": 0, "midtones": 0, "highlights": 0},
            },
            "hsl": hsl,
            "color_grading": {
                "shadows_color": (0, 0, 0),
                "midtones_color": (0, 0, 0),
                "highlights_color": (0, 0, 0),
                "shadows_strength": 0,
                "midtones_strength": 0,
                "highlights_strength": 0,
                "balance": 0,
                "split_highlight_h": 0,
                "split_highlight_s": 0,
                "split_shadow_h": 0,
                "split_shadow_s": 0,
            },
            "levels": levels,
        }

    def _default_geometry_settings(self) -> dict:  # DIFF-003-007
        return {
            "crop": {"left": 0, "top": 0, "right": 0, "bottom": 0},
            "rotate": 0.0,
            "straighten": 0.0,
            "perspective_h": 0.0,
            "perspective_v": 0.0,
            "distort_h": 0.0,
            "distort_v": 0.0,
            "scale_x": 100.0,
            "scale_y": 100.0,
            "flip_h": False,
            "flip_v": False,
        }

    def _collect_adjustment_params(self) -> dict:  # DIFF-003-001
        params = {}  # DIFF-003-001
        for key, slider in self._adjustment_sliders.items():  # DIFF-003-001
            scale = self._adjustment_scales.get(key, 1)  # DIFF-003-001
            params[key] = slider.value() / scale  # DIFF-003-001
        return params  # DIFF-003-001

    def _apply_edit_pipeline(self, image: QImage, preview: bool) -> QImage:  # DIFF-003-001
        if image.isNull():  # DIFF-003-001
            return image  # DIFF-003-001
        params = self._collect_adjustment_params()  # DIFF-003-001
        base = self._apply_geometry(image)  # DIFF-003-007
        working = base  # DIFF-003-001
        working = self._apply_basic_tone(working, params)  # DIFF-003-002
        working = self._apply_white_balance(working, params)  # DIFF-003-003
        working = self._apply_tone_ranges(working, params)  # DIFF-003-002
        working = self._apply_curves(working)  # DIFF-003-006
        working = self._apply_levels(working)  # DIFF-003-006
        working = self._apply_hsl_mix(working)  # DIFF-003-003
        working = self._apply_color_grading(working)  # DIFF-003-006
        working = self._apply_dehaze(working, params)  # DIFF-003-005
        working = self._apply_noise_reduction(working, params, preview)  # DIFF-003-005
        working = self._apply_texture_sharpness(working, params, preview)  # DIFF-003-004
        working = self._apply_effects(working, params, preview)  # DIFF-003-005
        if hasattr(self, "brush_toggle") and self.brush_toggle.isChecked():  # DIFF-003-007
            working = self._apply_brush_mask(base, working)  # DIFF-003-007
        return working  # DIFF-003-001

    def _apply_geometry(self, image: QImage) -> QImage:  # DIFF-003-007
        settings = self._geometry_settings  # DIFF-003-007
        out = image  # DIFF-003-007
        crop = settings.get("crop", {})  # DIFF-003-007
        if any(crop.get(k, 0) for k in ("left", "top", "right", "bottom")):  # DIFF-003-007
            left = int(out.width() * (crop.get("left", 0) / 100.0))  # DIFF-003-007
            top = int(out.height() * (crop.get("top", 0) / 100.0))  # DIFF-003-007
            right = int(out.width() * (crop.get("right", 0) / 100.0))  # DIFF-003-007
            bottom = int(out.height() * (crop.get("bottom", 0) / 100.0))  # DIFF-003-007
            width = max(1, out.width() - left - right)  # DIFF-003-007
            height = max(1, out.height() - top - bottom)  # DIFF-003-007
            out = out.copy(left, top, width, height)  # DIFF-003-007
        transform = QTransform()  # DIFF-003-007
        if settings.get("flip_h"):  # DIFF-003-007
            transform.scale(-1, 1)  # DIFF-003-007
        if settings.get("flip_v"):  # DIFF-003-007
            transform.scale(1, -1)  # DIFF-003-007
        angle = float(settings.get("rotate", 0.0)) + float(settings.get("straighten", 0.0))  # DIFF-003-007
        if abs(angle) > 0.001:  # DIFF-003-007
            transform.rotate(angle)  # DIFF-003-007
        persp_h = settings.get("perspective_h", 0.0) / 100.0  # DIFF-003-007
        persp_v = settings.get("perspective_v", 0.0) / 100.0  # DIFF-003-007
        if abs(persp_h) > 0.001 or abs(persp_v) > 0.001:  # DIFF-003-007
            transform.shear(persp_h, persp_v)  # DIFF-003-007
        dist_h = settings.get("distort_h", 0.0) / 100.0  # DIFF-003-007
        dist_v = settings.get("distort_v", 0.0) / 100.0  # DIFF-003-007
        if abs(dist_h) > 0.001 or abs(dist_v) > 0.001:  # DIFF-003-007
            transform.shear(dist_h, dist_v)  # DIFF-003-007
        if not transform.isIdentity():  # DIFF-003-007
            out = out.transformed(transform, Qt.SmoothTransformation)  # DIFF-003-007
        scale_x = settings.get("scale_x", 100.0) / 100.0  # DIFF-003-007
        scale_y = settings.get("scale_y", 100.0) / 100.0  # DIFF-003-007
        if abs(scale_x - 1.0) > 0.001 or abs(scale_y - 1.0) > 0.001:  # DIFF-003-007
            width = max(1, int(out.width() * scale_x))  # DIFF-003-007
            height = max(1, int(out.height() * scale_y))  # DIFF-003-007
            out = out.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)  # DIFF-003-007
        return out  # DIFF-003-007

    def _apply_basic_tone(self, image: QImage, params: dict) -> QImage:  # DIFF-003-002
        exposure = float(params.get("exposure", 0.0))  # DIFF-003-002
        brightness = float(params.get("brightness", 0.0))  # DIFF-003-002
        contrast = float(params.get("contrast", 0.0))  # DIFF-003-002
        gamma = float(params.get("gamma", 1.0))  # DIFF-003-002
        black_point = float(params.get("black_point", 0.0))  # DIFF-003-002
        white_point = float(params.get("white_point", 0.0))  # DIFF-003-002
        if (  # DIFF-003-002
            abs(exposure) < 0.001  # DIFF-003-002
            and abs(brightness) < 0.001  # DIFF-003-002
            and abs(contrast) < 0.001  # DIFF-003-002
            and abs(gamma - 1.0) < 0.001  # DIFF-003-002
            and abs(black_point) < 0.001  # DIFF-003-002
            and abs(white_point) < 0.001  # DIFF-003-002
        ):  # DIFF-003-002
            return image  # DIFF-003-002
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-002
        exp_factor = 2 ** exposure  # DIFF-003-002
        contrast_factor = (259 * (contrast + 255)) / (255 * (259 - contrast)) if contrast != 0 else 1.0  # DIFF-003-002
        gamma_inv = 1.0 / max(0.1, gamma)  # DIFF-003-002
        black = int(black_point / 100.0 * 64)  # DIFF-003-002
        white = int(255 + (white_point / 100.0 * 64))  # DIFF-003-002
        black = max(0, min(254, black))  # DIFF-003-002
        white = max(black + 1, min(255, white))  # DIFF-003-002
        width = out.width()  # DIFF-003-002
        height = out.height()  # DIFF-003-002
        for y in range(height):  # DIFF-003-002
            for x in range(width):  # DIFF-003-002
                color = out.pixelColor(x, y)  # DIFF-003-002
                r = color.red() * exp_factor + brightness  # DIFF-003-002
                g = color.green() * exp_factor + brightness  # DIFF-003-002
                b = color.blue() * exp_factor + brightness  # DIFF-003-002
                r = ((r - 128) * contrast_factor) + 128  # DIFF-003-002
                g = ((g - 128) * contrast_factor) + 128  # DIFF-003-002
                b = ((b - 128) * contrast_factor) + 128  # DIFF-003-002
                r = 255 * ((max(0.0, r) / 255.0) ** gamma_inv)  # DIFF-003-002
                g = 255 * ((max(0.0, g) / 255.0) ** gamma_inv)  # DIFF-003-002
                b = 255 * ((max(0.0, b) / 255.0) ** gamma_inv)  # DIFF-003-002
                r = (r - black) * 255 / (white - black)  # DIFF-003-002
                g = (g - black) * 255 / (white - black)  # DIFF-003-002
                b = (b - black) * 255 / (white - black)  # DIFF-003-002
                out.setPixelColor(  # DIFF-003-002
                    x,  # DIFF-003-002
                    y,  # DIFF-003-002
                    QColor(self._clamp_channel(r), self._clamp_channel(g), self._clamp_channel(b), color.alpha()),  # DIFF-003-002
                )  # DIFF-003-002
        return out  # DIFF-003-002

    def _apply_white_balance(self, image: QImage, params: dict) -> QImage:  # DIFF-003-003
        temperature = float(params.get("temperature", 6500.0))  # DIFF-003-003
        tint = float(params.get("tint", 0.0))  # DIFF-003-003
        saturation = float(params.get("saturation", 0.0))  # DIFF-003-003
        vibrance = float(params.get("vibrance", 0.0))  # DIFF-003-003
        hue_shift = float(params.get("hue", 0.0))  # DIFF-003-003
        if (  # DIFF-003-003
            abs(temperature - 6500.0) < 0.001  # DIFF-003-003
            and abs(tint) < 0.001  # DIFF-003-003
            and abs(saturation) < 0.001  # DIFF-003-003
            and abs(vibrance) < 0.001  # DIFF-003-003
            and abs(hue_shift) < 0.001  # DIFF-003-003
        ):  # DIFF-003-003
            return image  # DIFF-003-003
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-003
        temp_shift = ((temperature - 6500.0) / 6500.0) * 40.0  # DIFF-003-003
        sat_factor = 1.0 + (saturation / 100.0)  # DIFF-003-003
        vib_factor = vibrance / 100.0  # DIFF-003-003
        width = out.width()  # DIFF-003-003
        height = out.height()  # DIFF-003-003
        for y in range(height):  # DIFF-003-003
            for x in range(width):  # DIFF-003-003
                color = out.pixelColor(x, y)  # DIFF-003-003
                r = color.red() + temp_shift - (tint * 0.5)  # DIFF-003-003
                g = color.green() + tint  # DIFF-003-003
                b = color.blue() - temp_shift - (tint * 0.5)  # DIFF-003-003
                r = self._clamp_channel(r)  # DIFF-003-003
                g = self._clamp_channel(g)  # DIFF-003-003
                b = self._clamp_channel(b)  # DIFF-003-003
                hsv = QColor(r, g, b, color.alpha())  # DIFF-003-003
                h, s, v, a = hsv.getHsv()  # DIFF-003-003
                if h >= 0:  # DIFF-003-003
                    h = int((h + hue_shift) % 360)  # DIFF-003-003
                    s = int(max(0, min(255, s * sat_factor)))  # DIFF-003-003
                    if vib_factor != 0:  # DIFF-003-003
                        s = int(max(0, min(255, s + (255 - s) * vib_factor)))  # DIFF-003-003
                hsv.setHsv(h, s, v, a)  # DIFF-003-003
                out.setPixelColor(x, y, hsv)  # DIFF-003-003
        return out  # DIFF-003-003

    def _apply_tone_ranges(self, image: QImage, params: dict) -> QImage:  # DIFF-003-002
        highlights = float(params.get("highlights", 0.0))  # DIFF-003-002
        shadows = float(params.get("shadows", 0.0))  # DIFF-003-002
        whites = float(params.get("whites", 0.0))  # DIFF-003-002
        blacks = float(params.get("blacks", 0.0))  # DIFF-003-002
        if abs(highlights) < 0.001 and abs(shadows) < 0.001 and abs(whites) < 0.001 and abs(blacks) < 0.001:  # DIFF-003-002
            return image  # DIFF-003-002
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-002
        width = out.width()  # DIFF-003-002
        height = out.height()  # DIFF-003-002
        for y in range(height):  # DIFF-003-002
            for x in range(width):  # DIFF-003-002
                color = out.pixelColor(x, y)  # DIFF-003-002
                r = color.red()  # DIFF-003-002
                g = color.green()  # DIFF-003-002
                b = color.blue()  # DIFF-003-002
                luma = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0  # DIFF-003-002
                if highlights != 0:  # DIFF-003-002
                    weight = max(0.0, (luma - 0.5) / 0.5)  # DIFF-003-002
                    delta = highlights / 100.0 * 255.0 * weight  # DIFF-003-002
                    r += delta  # DIFF-003-002
                    g += delta  # DIFF-003-002
                    b += delta  # DIFF-003-002
                if shadows != 0:  # DIFF-003-002
                    weight = max(0.0, (0.5 - luma) / 0.5)  # DIFF-003-002
                    delta = shadows / 100.0 * 255.0 * weight  # DIFF-003-002
                    r += delta  # DIFF-003-002
                    g += delta  # DIFF-003-002
                    b += delta  # DIFF-003-002
                if whites != 0:  # DIFF-003-002
                    weight = max(0.0, (luma - 0.75) / 0.25)  # DIFF-003-002
                    delta = whites / 100.0 * 255.0 * weight  # DIFF-003-002
                    r += delta  # DIFF-003-002
                    g += delta  # DIFF-003-002
                    b += delta  # DIFF-003-002
                if blacks != 0:  # DIFF-003-002
                    weight = max(0.0, (0.25 - luma) / 0.25)  # DIFF-003-002
                    delta = blacks / 100.0 * 255.0 * weight  # DIFF-003-002
                    r += delta  # DIFF-003-002
                    g += delta  # DIFF-003-002
                    b += delta  # DIFF-003-002
                out.setPixelColor(  # DIFF-003-002
                    x,  # DIFF-003-002
                    y,  # DIFF-003-002
                    QColor(self._clamp_channel(r), self._clamp_channel(g), self._clamp_channel(b), color.alpha()),  # DIFF-003-002
                )  # DIFF-003-002
        return out  # DIFF-003-002

    def _apply_curves(self, image: QImage) -> QImage:  # DIFF-003-006
        curves = self._advanced_settings["curves"]  # DIFF-003-006
        if all(curves[key][slot] == 0 for key in curves for slot in curves[key]):  # DIFF-003-006
            return image  # DIFF-003-006
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-006
        rgb_lut = self._build_curve_lut(curves["rgb"])  # DIFF-003-006
        out = self._apply_lut(out, rgb_lut, rgb_lut, rgb_lut)  # DIFF-003-006
        for channel, idx in (("r", 0), ("g", 1), ("b", 2)):  # DIFF-003-006
            curve = curves[channel]  # DIFF-003-006
            if curve["shadows"] == 0 and curve["midtones"] == 0 and curve["highlights"] == 0:  # DIFF-003-006
                continue  # DIFF-003-006
            lut = self._build_curve_lut(curve)  # DIFF-003-006
            if idx == 0:  # DIFF-003-006
                out = self._apply_lut(out, lut, None, None)  # DIFF-003-006
            elif idx == 1:  # DIFF-003-006
                out = self._apply_lut(out, None, lut, None)  # DIFF-003-006
            else:  # DIFF-003-006
                out = self._apply_lut(out, None, None, lut)  # DIFF-003-006
        return out  # DIFF-003-006

    def _apply_levels(self, image: QImage) -> QImage:  # DIFF-003-006
        levels = self._advanced_settings["levels"]  # DIFF-003-006
        global_levels = levels["global"]  # DIFF-003-006
        channels = levels["channels"]  # DIFF-003-006
        defaults = {"in_black": 0, "in_gamma": 1.0, "in_white": 255, "out_black": 0, "out_white": 255}  # DIFF-003-006
        if global_levels == defaults and all(channels[c] == defaults for c in channels):  # DIFF-003-006
            return image  # DIFF-003-006
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-006
        width = out.width()  # DIFF-003-006
        height = out.height()  # DIFF-003-006
        for y in range(height):  # DIFF-003-006
            for x in range(width):  # DIFF-003-006
                color = out.pixelColor(x, y)  # DIFF-003-006
                r = self._apply_levels_value(color.red(), global_levels)  # DIFF-003-006
                g = self._apply_levels_value(color.green(), global_levels)  # DIFF-003-006
                b = self._apply_levels_value(color.blue(), global_levels)  # DIFF-003-006
                r = self._apply_levels_value(r, channels["r"])  # DIFF-003-006
                g = self._apply_levels_value(g, channels["g"])  # DIFF-003-006
                b = self._apply_levels_value(b, channels["b"])  # DIFF-003-006
                out.setPixelColor(x, y, QColor(r, g, b, color.alpha()))  # DIFF-003-006
        return out  # DIFF-003-006

    def _apply_hsl_mix(self, image: QImage) -> QImage:  # DIFF-003-003
        hsl = self._advanced_settings["hsl"]  # DIFF-003-003
        if all(hsl[band]["h"] == 0 and hsl[band]["s"] == 0 and hsl[band]["l"] == 0 for band in hsl):  # DIFF-003-003
            return image  # DIFF-003-003
        centers = {  # DIFF-003-003
            "red": 0,  # DIFF-003-003
            "orange": 30,  # DIFF-003-003
            "yellow": 60,  # DIFF-003-003
            "green": 120,  # DIFF-003-003
            "aqua": 180,  # DIFF-003-003
            "blue": 240,  # DIFF-003-003
            "purple": 270,  # DIFF-003-003
            "magenta": 300,  # DIFF-003-003
        }  # DIFF-003-003
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-003
        width = out.width()  # DIFF-003-003
        height = out.height()  # DIFF-003-003
        for y in range(height):  # DIFF-003-003
            for x in range(width):  # DIFF-003-003
                color = out.pixelColor(x, y)  # DIFF-003-003
                h, s, v, a = color.getHsv()  # DIFF-003-003
                if h < 0:  # DIFF-003-003
                    continue  # DIFF-003-003
                h_adj = 0.0  # DIFF-003-003
                s_adj = 0.0  # DIFF-003-003
                l_adj = 0.0  # DIFF-003-003
                for band, center in centers.items():  # DIFF-003-003
                    diff = abs((h - center + 180) % 360 - 180)  # DIFF-003-003
                    if diff > 30:  # DIFF-003-003
                        continue  # DIFF-003-003
                    weight = 1.0 - (diff / 30.0)  # DIFF-003-003
                    h_adj += hsl[band]["h"] * weight  # DIFF-003-003
                    s_adj += hsl[band]["s"] * weight  # DIFF-003-003
                    l_adj += hsl[band]["l"] * weight  # DIFF-003-003
                h = int((h + h_adj) % 360)  # DIFF-003-003
                s = int(max(0, min(255, s + (s_adj / 100.0) * 255)))  # DIFF-003-003
                v = int(max(0, min(255, v + (l_adj / 100.0) * 255)))  # DIFF-003-003
                color.setHsv(h, s, v, a)  # DIFF-003-003
                out.setPixelColor(x, y, color)  # DIFF-003-003
        return out  # DIFF-003-003

    def _apply_color_grading(self, image: QImage) -> QImage:  # DIFF-003-006
        grading = self._advanced_settings["color_grading"]  # DIFF-003-006
        if all(grading[f"{key}_strength"] == 0 for key in ("shadows", "midtones", "highlights")) and grading["split_highlight_s"] == 0 and grading["split_shadow_s"] == 0:  # DIFF-003-006
            return image  # DIFF-003-006
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-006
        width = out.width()  # DIFF-003-006
        height = out.height()  # DIFF-003-006
        balance = grading["balance"] / 100.0  # DIFF-003-006
        split_high = QColor.fromHsv(grading["split_highlight_h"], int(grading["split_highlight_s"] * 2.55), 255)  # DIFF-003-006
        split_shadow = QColor.fromHsv(grading["split_shadow_h"], int(grading["split_shadow_s"] * 2.55), 255)  # DIFF-003-006
        for y in range(height):  # DIFF-003-006
            for x in range(width):  # DIFF-003-006
                color = out.pixelColor(x, y)  # DIFF-003-006
                r = color.red()  # DIFF-003-006
                g = color.green()  # DIFF-003-006
                b = color.blue()  # DIFF-003-006
                luma = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0  # DIFF-003-006
                shadows_weight = max(0.0, (0.5 - luma) / 0.5)  # DIFF-003-006
                highlights_weight = max(0.0, (luma - 0.5) / 0.5)  # DIFF-003-006
                midtones_weight = 1.0 - abs(luma - 0.5) * 2.0  # DIFF-003-006
                shadows_weight = max(0.0, min(1.0, shadows_weight - balance))  # DIFF-003-006
                highlights_weight = max(0.0, min(1.0, highlights_weight + balance))  # DIFF-003-006
                midtones_weight = max(0.0, min(1.0, midtones_weight))  # DIFF-003-006
                for key, weight in (("shadows", shadows_weight), ("midtones", midtones_weight), ("highlights", highlights_weight)):  # DIFF-003-006
                    strength = grading[f"{key}_strength"] / 100.0  # DIFF-003-006
                    if strength == 0 or weight == 0:  # DIFF-003-006
                        continue  # DIFF-003-006
                    color_target = grading[f"{key}_color"]  # DIFF-003-006
                    r = r * (1 - strength * weight) + color_target[0] * (strength * weight)  # DIFF-003-006
                    g = g * (1 - strength * weight) + color_target[1] * (strength * weight)  # DIFF-003-006
                    b = b * (1 - strength * weight) + color_target[2] * (strength * weight)  # DIFF-003-006
                if grading["split_shadow_s"] > 0 and shadows_weight > 0:  # DIFF-003-006
                    r = r * (1 - shadows_weight * 0.2) + split_shadow.red() * (shadows_weight * 0.2)  # DIFF-003-006
                    g = g * (1 - shadows_weight * 0.2) + split_shadow.green() * (shadows_weight * 0.2)  # DIFF-003-006
                    b = b * (1 - shadows_weight * 0.2) + split_shadow.blue() * (shadows_weight * 0.2)  # DIFF-003-006
                if grading["split_highlight_s"] > 0 and highlights_weight > 0:  # DIFF-003-006
                    r = r * (1 - highlights_weight * 0.2) + split_high.red() * (highlights_weight * 0.2)  # DIFF-003-006
                    g = g * (1 - highlights_weight * 0.2) + split_high.green() * (highlights_weight * 0.2)  # DIFF-003-006
                    b = b * (1 - highlights_weight * 0.2) + split_high.blue() * (highlights_weight * 0.2)  # DIFF-003-006
                out.setPixelColor(  # DIFF-003-006
                    x,  # DIFF-003-006
                    y,  # DIFF-003-006
                    QColor(self._clamp_channel(r), self._clamp_channel(g), self._clamp_channel(b), color.alpha()),  # DIFF-003-006
                )  # DIFF-003-006
        return out  # DIFF-003-006

    def _apply_dehaze(self, image: QImage, params: dict) -> QImage:  # DIFF-003-005
        dehaze = float(params.get("dehaze", 0.0))  # DIFF-003-005
        haze_removal = float(params.get("haze_removal", 0.0))  # DIFF-003-005
        defog = float(params.get("defog", 0.0))  # DIFF-003-005
        amount = (dehaze + haze_removal + defog) / 300.0  # DIFF-003-005
        if abs(amount) < 0.001:  # DIFF-003-005
            return image  # DIFF-003-005
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-005
        width = out.width()  # DIFF-003-005
        height = out.height()  # DIFF-003-005
        for y in range(height):  # DIFF-003-005
            for x in range(width):  # DIFF-003-005
                color = out.pixelColor(x, y)  # DIFF-003-005
                r = color.red()  # DIFF-003-005
                g = color.green()  # DIFF-003-005
                b = color.blue()  # DIFF-003-005
                r = ((r - 128) * (1 + amount)) + 128  # DIFF-003-005
                g = ((g - 128) * (1 + amount)) + 128  # DIFF-003-005
                b = ((b - 128) * (1 + amount)) + 128  # DIFF-003-005
                out.setPixelColor(  # DIFF-003-005
                    x,  # DIFF-003-005
                    y,  # DIFF-003-005
                    QColor(self._clamp_channel(r), self._clamp_channel(g), self._clamp_channel(b), color.alpha()),  # DIFF-003-005
                )  # DIFF-003-005
        return out  # DIFF-003-005

    def _apply_noise_reduction(self, image: QImage, params: dict, preview: bool) -> QImage:  # DIFF-003-005
        luma = float(params.get("noise_reduction_luma", 0.0))  # DIFF-003-005
        color = float(params.get("noise_reduction_color", 0.0))  # DIFF-003-005
        denoise = float(params.get("denoise_amount", 0.0))  # DIFF-003-005
        detail = float(params.get("denoise_detail", 0.0))  # DIFF-003-005
        grain_reduction = float(params.get("grain_reduction", 0.0))  # DIFF-003-005
        smoothing = float(params.get("skin_smoothing", 0.0))  # DIFF-003-005
        total = max(luma, color, denoise, grain_reduction, smoothing)  # DIFF-003-005
        if total <= 0.0:  # DIFF-003-005
            return image  # DIFF-003-005
        radius = max(1, int(total / 25))  # DIFF-003-005
        if preview:  # DIFF-003-005
            radius = max(1, min(6, radius))  # DIFF-003-005
        blurred = self._blur_image(image, radius)  # DIFF-003-005
        mix = max(0.0, min(1.0, (total / 100.0) * (1.0 - detail / 100.0)))  # DIFF-003-005
        return self._blend_images(image, blurred, mix)  # DIFF-003-005

    def _apply_texture_sharpness(self, image: QImage, params: dict, preview: bool) -> QImage:  # DIFF-003-004
        clarity = float(params.get("clarity", 0.0))  # DIFF-003-004
        texture = float(params.get("texture", 0.0))  # DIFF-003-004
        structure = float(params.get("structure", 0.0))  # DIFF-003-004
        midtone_contrast = float(params.get("midtone_contrast", 0.0))  # DIFF-003-004
        local_contrast = float(params.get("local_contrast", 0.0))  # DIFF-003-004
        clarity_pop = float(params.get("clarity_pop", 0.0))  # DIFF-003-004
        sharpen_amount = float(params.get("sharpen_amount", 0.0))  # DIFF-003-004
        sharpening = float(params.get("sharpening", 0.0))  # DIFF-003-004
        unsharp = float(params.get("unsharp_mask", 0.0))  # DIFF-003-004
        sharpen_radius = float(params.get("sharpen_radius", 1.0))  # DIFF-003-004
        sharpen_threshold = float(params.get("sharpen_threshold", 0.0))  # DIFF-003-004
        detail = float(params.get("detail", 0.0))  # DIFF-003-004
        edge_masking = float(params.get("edge_masking", 0.0))  # DIFF-003-004
        out = image  # DIFF-003-004
        local_amount = (clarity + texture + structure + midtone_contrast + local_contrast + clarity_pop) / 600.0  # DIFF-003-004
        if abs(local_amount) > 0.001:  # DIFF-003-004
            radius = 2 if preview else 3  # DIFF-003-004
            out = self._apply_unsharp_mask(out, abs(local_amount), radius, 0)  # DIFF-003-004
        sharp_amount = (sharpen_amount + sharpening + unsharp) / 300.0  # DIFF-003-004
        if abs(sharp_amount) > 0.001 or detail > 0:  # DIFF-003-004
            radius = max(1, int(round(sharpen_radius)))  # DIFF-003-004
            threshold = max(0, int(sharpen_threshold + edge_masking * 0.5))  # DIFF-003-004
            amount = max(0.0, min(1.0, abs(sharp_amount) + detail / 200.0))  # DIFF-003-004
            out = self._apply_unsharp_mask(out, amount, radius, threshold)  # DIFF-003-004
        return out  # DIFF-003-004

    def _apply_effects(self, image: QImage, params: dict, preview: bool) -> QImage:  # DIFF-003-005
        vignette = float(params.get("vignette", 0.0))  # DIFF-003-005
        fade = float(params.get("fade", 0.0))  # DIFF-003-005
        grain = float(params.get("grain", 0.0))  # DIFF-003-005
        glow = float(params.get("glow", 0.0))  # DIFF-003-005
        lens_blur = float(params.get("lens_blur", 0.0))  # DIFF-003-005
        motion_blur = float(params.get("motion_blur", 0.0))  # DIFF-003-005
        high_pass = float(params.get("high_pass", 0.0))  # DIFF-003-005
        out = image  # DIFF-003-005
        if abs(lens_blur) > 0.001:  # DIFF-003-005
            radius = max(1, int(lens_blur / 20))  # DIFF-003-005
            out = self._blur_image(out, radius)  # DIFF-003-005
        if abs(motion_blur) > 0.001:  # DIFF-003-005
            out = self._apply_motion_blur(out, motion_blur)  # DIFF-003-005
        if abs(glow) > 0.001:  # DIFF-003-005
            radius = max(1, int(glow / 20))  # DIFF-003-005
            blurred = self._blur_image(out, radius)  # DIFF-003-005
            out = self._blend_images(out, blurred, min(1.0, glow / 100.0))  # DIFF-003-005
        if abs(high_pass) > 0.001:  # DIFF-003-005
            radius = max(1, int(high_pass / 25))  # DIFF-003-005
            blurred = self._blur_image(out, radius)  # DIFF-003-005
            out = self._apply_high_pass(out, blurred, high_pass / 100.0)  # DIFF-003-005
        if abs(vignette) > 0.001:  # DIFF-003-005
            out = self._apply_vignette(out, vignette)  # DIFF-003-005
        if abs(fade) > 0.001:  # DIFF-003-005
            out = self._apply_fade(out, fade)  # DIFF-003-005
        if abs(grain) > 0.001:  # DIFF-003-005
            out = self._apply_grain(out, grain)  # DIFF-003-005
        return out  # DIFF-003-005

    def _apply_brush_mask(self, base: QImage, adjusted: QImage) -> QImage:  # DIFF-003-007
        if self._brush_mask is None:  # DIFF-003-007
            return adjusted  # DIFF-003-007
        mask = self._brush_mask  # DIFF-003-007
        if mask.size() != adjusted.size():  # DIFF-003-007
            mask = mask.scaled(adjusted.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)  # DIFF-003-007
        base_argb = base.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-007
        adj_argb = adjusted.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-007
        out = adj_argb.copy()  # DIFF-003-007
        width = out.width()  # DIFF-003-007
        height = out.height()  # DIFF-003-007
        for y in range(height):  # DIFF-003-007
            for x in range(width):  # DIFF-003-007
                weight = mask.pixelColor(x, y).red() / 255.0  # DIFF-003-007
                if weight <= 0:  # DIFF-003-007
                    out.setPixelColor(x, y, base_argb.pixelColor(x, y))  # DIFF-003-007
                    continue  # DIFF-003-007
                if weight >= 1:  # DIFF-003-007
                    continue  # DIFF-003-007
                base_color = base_argb.pixelColor(x, y)  # DIFF-003-007
                adj_color = adj_argb.pixelColor(x, y)  # DIFF-003-007
                r = base_color.red() * (1 - weight) + adj_color.red() * weight  # DIFF-003-007
                g = base_color.green() * (1 - weight) + adj_color.green() * weight  # DIFF-003-007
                b = base_color.blue() * (1 - weight) + adj_color.blue() * weight  # DIFF-003-007
                out.setPixelColor(x, y, QColor(int(r), int(g), int(b), adj_color.alpha()))  # DIFF-003-007
        return out  # DIFF-003-007

    def _build_curve_lut(self, curve: dict) -> list[int]:  # DIFF-003-006
        offsets = {  # DIFF-003-006
            "shadows": curve.get("shadows", 0),  # DIFF-003-006
            "midtones": curve.get("midtones", 0),  # DIFF-003-006
            "highlights": curve.get("highlights", 0),  # DIFF-003-006
        }  # DIFF-003-006
        points = [  # DIFF-003-006
            (0, 0),  # DIFF-003-006
            (64, max(0, min(255, 64 + offsets["shadows"] * 0.64))),  # DIFF-003-006
            (128, max(0, min(255, 128 + offsets["midtones"] * 0.64))),  # DIFF-003-006
            (192, max(0, min(255, 192 + offsets["highlights"] * 0.64))),  # DIFF-003-006
            (255, 255),  # DIFF-003-006
        ]  # DIFF-003-006
        lut = [0] * 256  # DIFF-003-006
        for idx in range(len(points) - 1):  # DIFF-003-006
            x0, y0 = points[idx]  # DIFF-003-006
            x1, y1 = points[idx + 1]  # DIFF-003-006
            span = max(1, x1 - x0)  # DIFF-003-006
            for x in range(x0, x1 + 1):  # DIFF-003-006
                t = (x - x0) / span  # DIFF-003-006
                lut[x] = int(round(y0 + (y1 - y0) * t))  # DIFF-003-006
        return lut  # DIFF-003-006

    def _apply_lut(self, image: QImage, lut_r, lut_g, lut_b) -> QImage:  # DIFF-003-006
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-006
        width = out.width()  # DIFF-003-006
        height = out.height()  # DIFF-003-006
        for y in range(height):  # DIFF-003-006
            for x in range(width):  # DIFF-003-006
                color = out.pixelColor(x, y)  # DIFF-003-006
                r = lut_r[color.red()] if lut_r else color.red()  # DIFF-003-006
                g = lut_g[color.green()] if lut_g else color.green()  # DIFF-003-006
                b = lut_b[color.blue()] if lut_b else color.blue()  # DIFF-003-006
                out.setPixelColor(x, y, QColor(r, g, b, color.alpha()))  # DIFF-003-006
        return out  # DIFF-003-006

    def _apply_levels_value(self, value: int, settings: dict) -> int:  # DIFF-003-006
        in_black = settings["in_black"]  # DIFF-003-006
        in_white = settings["in_white"]  # DIFF-003-006
        if in_white <= in_black:  # DIFF-003-006
            return value  # DIFF-003-006
        out_black = settings["out_black"]  # DIFF-003-006
        out_white = settings["out_white"]  # DIFF-003-006
        gamma = settings["in_gamma"]  # DIFF-003-006
        norm = (value - in_black) / (in_white - in_black)  # DIFF-003-006
        norm = max(0.0, min(1.0, norm))  # DIFF-003-006
        norm = norm ** (1.0 / max(0.1, gamma))  # DIFF-003-006
        out = out_black + norm * (out_white - out_black)  # DIFF-003-006
        return int(max(0, min(255, out)))  # DIFF-003-006

    def _blur_image(self, image: QImage, radius: int) -> QImage:  # DIFF-003-005
        if radius <= 0:  # DIFF-003-005
            return image  # DIFF-003-005
        scale = max(1, min(radius, 12))  # DIFF-003-005
        width = max(1, image.width() // scale)  # DIFF-003-005
        height = max(1, image.height() // scale)  # DIFF-003-005
        small = image.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)  # DIFF-003-005
        return small.scaled(image.width(), image.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)  # DIFF-003-005

    def _blend_images(self, base: QImage, overlay: QImage, amount: float) -> QImage:  # DIFF-003-005
        amount = max(0.0, min(1.0, amount))  # DIFF-003-005
        if amount == 0.0:  # DIFF-003-005
            return base  # DIFF-003-005
        base_argb = base.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-005
        overlay_argb = overlay.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-005
        out = base_argb.copy()  # DIFF-003-005
        width = out.width()  # DIFF-003-005
        height = out.height()  # DIFF-003-005
        for y in range(height):  # DIFF-003-005
            for x in range(width):  # DIFF-003-005
                base_color = base_argb.pixelColor(x, y)  # DIFF-003-005
                overlay_color = overlay_argb.pixelColor(x, y)  # DIFF-003-005
                r = base_color.red() * (1 - amount) + overlay_color.red() * amount  # DIFF-003-005
                g = base_color.green() * (1 - amount) + overlay_color.green() * amount  # DIFF-003-005
                b = base_color.blue() * (1 - amount) + overlay_color.blue() * amount  # DIFF-003-005
                out.setPixelColor(x, y, QColor(int(r), int(g), int(b), base_color.alpha()))  # DIFF-003-005
        return out  # DIFF-003-005

    def _apply_unsharp_mask(self, image: QImage, amount: float, radius: int, threshold: int) -> QImage:  # DIFF-003-004
        if amount <= 0.0:  # DIFF-003-004
            return image  # DIFF-003-004
        blurred = self._blur_image(image, radius)  # DIFF-003-004
        base = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-004
        blur = blurred.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-004
        out = base.copy()  # DIFF-003-004
        width = out.width()  # DIFF-003-004
        height = out.height()  # DIFF-003-004
        for y in range(height):  # DIFF-003-004
            for x in range(width):  # DIFF-003-004
                bc = base.pixelColor(x, y)  # DIFF-003-004
                bl = blur.pixelColor(x, y)  # DIFF-003-004
                dr = bc.red() - bl.red()  # DIFF-003-004
                dg = bc.green() - bl.green()  # DIFF-003-004
                db = bc.blue() - bl.blue()  # DIFF-003-004
                if abs(dr) < threshold and abs(dg) < threshold and abs(db) < threshold:  # DIFF-003-004
                    continue  # DIFF-003-004
                r = bc.red() + dr * amount  # DIFF-003-004
                g = bc.green() + dg * amount  # DIFF-003-004
                b = bc.blue() + db * amount  # DIFF-003-004
                out.setPixelColor(x, y, QColor(self._clamp_channel(r), self._clamp_channel(g), self._clamp_channel(b), bc.alpha()))  # DIFF-003-004
        return out  # DIFF-003-004

    def _apply_motion_blur(self, image: QImage, amount: float) -> QImage:  # DIFF-003-005
        radius = max(1, int(abs(amount) / 20))  # DIFF-003-005
        if radius <= 1:  # DIFF-003-005
            return image  # DIFF-003-005
        out = QImage(image.size(), QImage.Format_ARGB32)  # DIFF-003-005
        out.fill(Qt.transparent)  # DIFF-003-005
        painter = QPainter(out)  # DIFF-003-005
        steps = max(2, radius)  # DIFF-003-005
        for idx in range(steps):  # DIFF-003-005
            offset = int((idx - steps / 2) * 1)  # DIFF-003-005
            painter.drawImage(offset, 0, image)  # DIFF-003-005
        painter.end()  # DIFF-003-005
        return out  # DIFF-003-005

    def _apply_high_pass(self, base: QImage, blurred: QImage, amount: float) -> QImage:  # DIFF-003-005
        base_argb = base.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-005
        blur = blurred.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-005
        out = base_argb.copy()  # DIFF-003-005
        width = out.width()  # DIFF-003-005
        height = out.height()  # DIFF-003-005
        for y in range(height):  # DIFF-003-005
            for x in range(width):  # DIFF-003-005
                bc = base_argb.pixelColor(x, y)  # DIFF-003-005
                bl = blur.pixelColor(x, y)  # DIFF-003-005
                r = bc.red() + (bc.red() - bl.red()) * amount  # DIFF-003-005
                g = bc.green() + (bc.green() - bl.green()) * amount  # DIFF-003-005
                b = bc.blue() + (bc.blue() - bl.blue()) * amount  # DIFF-003-005
                out.setPixelColor(x, y, QColor(self._clamp_channel(r), self._clamp_channel(g), self._clamp_channel(b), bc.alpha()))  # DIFF-003-005
        return out  # DIFF-003-005

    def _apply_vignette(self, image: QImage, amount: float) -> QImage:  # DIFF-003-005
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-005
        width = out.width()  # DIFF-003-005
        height = out.height()  # DIFF-003-005
        center_x = width / 2  # DIFF-003-005
        center_y = height / 2  # DIFF-003-005
        max_dist = (center_x**2 + center_y**2) ** 0.5  # DIFF-003-005
        strength = amount / 100.0  # DIFF-003-005
        for y in range(height):  # DIFF-003-005
            for x in range(width):  # DIFF-003-005
                color = out.pixelColor(x, y)  # DIFF-003-005
                dx = x - center_x  # DIFF-003-005
                dy = y - center_y  # DIFF-003-005
                dist = (dx**2 + dy**2) ** 0.5  # DIFF-003-005
                factor = 1.0 - strength * (dist / max_dist)  # DIFF-003-005
                r = color.red() * factor  # DIFF-003-005
                g = color.green() * factor  # DIFF-003-005
                b = color.blue() * factor  # DIFF-003-005
                out.setPixelColor(x, y, QColor(self._clamp_channel(r), self._clamp_channel(g), self._clamp_channel(b), color.alpha()))  # DIFF-003-005
        return out  # DIFF-003-005

    def _apply_fade(self, image: QImage, amount: float) -> QImage:  # DIFF-003-005
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-005
        width = out.width()  # DIFF-003-005
        height = out.height()  # DIFF-003-005
        factor = amount / 100.0  # DIFF-003-005
        for y in range(height):  # DIFF-003-005
            for x in range(width):  # DIFF-003-005
                color = out.pixelColor(x, y)  # DIFF-003-005
                r = color.red() * (1 - factor) + 128 * factor  # DIFF-003-005
                g = color.green() * (1 - factor) + 128 * factor  # DIFF-003-005
                b = color.blue() * (1 - factor) + 128 * factor  # DIFF-003-005
                out.setPixelColor(x, y, QColor(self._clamp_channel(r), self._clamp_channel(g), self._clamp_channel(b), color.alpha()))  # DIFF-003-005
        return out  # DIFF-003-005

    def _apply_grain(self, image: QImage, amount: float) -> QImage:  # DIFF-003-005
        out = image.convertToFormat(QImage.Format_ARGB32)  # DIFF-003-005
        width = out.width()  # DIFF-003-005
        height = out.height()  # DIFF-003-005
        strength = amount / 100.0 * 32  # DIFF-003-005
        for y in range(height):  # DIFF-003-005
            for x in range(width):  # DIFF-003-005
                color = out.pixelColor(x, y)  # DIFF-003-005
                noise = ((x * 73856093) ^ (y * 19349663)) & 0xFF  # DIFF-003-005
                offset = (noise / 255.0 - 0.5) * 2 * strength  # DIFF-003-005
                r = color.red() + offset  # DIFF-003-005
                g = color.green() + offset  # DIFF-003-005
                b = color.blue() + offset  # DIFF-003-005
                out.setPixelColor(x, y, QColor(self._clamp_channel(r), self._clamp_channel(g), self._clamp_channel(b), color.alpha()))  # DIFF-003-005
        return out  # DIFF-003-005

    def _clamp_channel(self, value: float) -> int:  # DIFF-003-001
        return int(max(0, min(255, round(value))))  # DIFF-003-001

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
        layout.setContentsMargins(UI_OUTER_PADDING, UI_OUTER_PADDING, UI_OUTER_PADDING, UI_OUTER_PADDING)  # DIFF-001-001
        layout.setSpacing(UI_SECTION_GAP)  # DIFF-001-001

    def _apply_section_layout(self, layout: QVBoxLayout) -> None:
        layout.setContentsMargins(UI_SECTION_GAP, UI_SECTION_GAP, UI_SECTION_GAP, UI_SECTION_GAP)  # DIFF-001-001
        layout.setSpacing(UI_INNER_GAP)  # DIFF-001-001

    def _apply_tab_layout(self, layout: QVBoxLayout) -> None:
        layout.setContentsMargins(0, 0, 0, 0)  # DIFF-001-001
        layout.setSpacing(UI_SECTION_GAP)  # DIFF-001-001

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
