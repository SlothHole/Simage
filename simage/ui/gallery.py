"""
Gallery/search tab for Simage UI.
Fast, scrollable, async thumbnail grid for large image sets.
"""

import html
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
    QScrollArea,  # DIFF-001-004
    QPushButton,
    QComboBox,
    QMenu,
    QListWidget,
    QListWidgetItem,
    QSlider,
    QToolButton,
    QWidgetAction,
)
from PySide6.QtCore import Qt

from simage.utils.paths import resolve_repo_path
from .thumb_grid import ThumbnailGrid
from .record_filter import load_records, filter_records, filter_by_tags
from .thumbnails import THUMB_DIR, thumbnail_path_for_source
from .theme import (
    DEFAULT_THUMB_SIZE,
    DEFAULT_THUMB_SPACING,
    MAX_THUMB_SIZE,
    MAX_THUMB_SPACING,
    MIN_THUMB_SIZE,
    MIN_THUMB_SPACING,
    UI_OUTER_PADDING,  # DIFF-001-001
    UI_SECTION_GAP,  # DIFF-001-001
    UI_INNER_GAP,  # DIFF-001-001
    load_ui_settings,
    load_splitter_sizes,
    save_splitter_sizes,
    save_ui_settings,
)

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
        self._apply_page_layout(main_layout)
        splitter = QSplitter(Qt.Horizontal)

        # Left: Search/filter/sort + Thumbnail grid + batch controls + export
        grid_widget = QWidget()
        grid_widget.setMinimumWidth(480)  # DIFF-001-003
        grid_layout = QVBoxLayout(grid_widget)
        self._apply_section_layout(grid_layout)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by filename, metadata...")
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.apply_search)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(
            self._help_button(
                "Search filenames and metadata. Use key:value for field search; "
                "multiple terms are ANDed."
            )
        )

        self.tag_menu_btn = QToolButton()
        self.tag_menu_btn.setText("Filter Tags")
        self.tag_menu_btn.setPopupMode(QToolButton.InstantPopup)
        self.tag_menu = QMenu(self)
        self.tag_menu_btn.setMenu(self.tag_menu)
        self.tag_list = QListWidget()
        self.tag_list.setSelectionMode(QListWidget.NoSelection)
        self.tag_list.setFixedSize(280, 320)
        self.tag_list.itemChanged.connect(self._on_tag_item_changed)
        tag_action = QWidgetAction(self)
        tag_action.setDefaultWidget(self.tag_list)
        self.tag_menu.addAction(tag_action)
        search_layout.addWidget(self.tag_menu_btn)
        search_layout.addWidget(
            self._help_button(
                "Filter by prompt tags. Checked tags must all be present to match."
            )
        )

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Sort: File Name", "file_name")
        self.sort_combo.addItem("Sort: Created Date", "created_utc")
        self.sort_combo.addItem("Sort: Imported Date", "imported_utc")
        self.sort_combo.addItem("Sort: Tag Count", "tag_count")
        self.sort_combo.addItem("Sort: Width", "width")
        self.sort_combo.addItem("Sort: Height", "height")
        self.sort_combo.addItem("Sort: Steps", "steps")
        self.sort_combo.addItem("Sort: CFG Scale", "cfg_scale")
        self.sort_combo.addItem("Sort: Seed", "seed")
        self.sort_combo.addItem("Sort: Model", "model")
        self.sort_combo.addItem("Sort: Sampler", "sampler")
        self.sort_combo.addItem("Sort: Scheduler", "scheduler")
        self.sort_combo.addItem("Sort: Format", "format_hint")
        self.sort_combo.currentIndexChanged.connect(self.apply_sort)
        search_layout.addWidget(self.sort_combo)
        search_layout.addWidget(
            self._help_button("Sort the current results by the selected field.")
        )

        grid_layout.addLayout(search_layout)

        grid_header = QHBoxLayout()
        grid_header.addWidget(QLabel("Thumbnails"))
        grid_header.addWidget(
            self._help_button(
                "Thumbnail grid. Only images with existing originals and thumbnails are shown. "
                "Use arrow keys to move selection."
            )
        )
        grid_header.addStretch(1)
        grid_layout.addLayout(grid_header)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Thumbnail size"))
        self.thumb_size_slider = QSlider(Qt.Horizontal)
        self.thumb_size_slider.setRange(MIN_THUMB_SIZE, MAX_THUMB_SIZE)
        self.thumb_size_value = QLabel("")
        size_row.addWidget(self.thumb_size_slider)
        size_row.addWidget(self.thumb_size_value)
        size_row.addStretch(1)
        grid_layout.addLayout(size_row)

        spacing_row = QHBoxLayout()
        spacing_row.addWidget(QLabel("Thumbnail spacing"))
        self.thumb_spacing_slider = QSlider(Qt.Horizontal)
        self.thumb_spacing_slider.setRange(MIN_THUMB_SPACING, MAX_THUMB_SPACING)
        self.thumb_spacing_value = QLabel("")
        spacing_row.addWidget(self.thumb_spacing_slider)
        spacing_row.addWidget(self.thumb_spacing_value)
        spacing_row.addStretch(1)
        grid_layout.addLayout(spacing_row)

        self.grid = ThumbnailGrid()
        self.grid.image_selected.connect(self.on_image_selected)
        self.grid.images_selected.connect(self.on_images_selected)
        grid_layout.addWidget(self.grid)

        splitter.addWidget(grid_widget)

        # Right: Side panel (image preview + info, resizable)
        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        self._apply_section_layout(side_layout)
        detail_splitter = QSplitter(Qt.Horizontal)

        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        self._apply_section_layout(preview_layout)
        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel("Preview"))
        preview_header.addWidget(
            self._help_button("Shows the selected image. Drag the splitter to resize.")
        )
        preview_header.addStretch(1)
        preview_layout.addLayout(preview_header)
        self.image_preview = QLabel("No image selected")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumSize(0, 0)
        self.image_preview.setFrameShape(QFrame.Box)
        self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_layout.addWidget(self.image_preview)
        preview_panel.setLayout(preview_layout)

        self.info_window = QTextEdit()
        self.info_window.setReadOnly(True)
        self.info_window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        self._apply_section_layout(info_layout)
        info_header = QHBoxLayout()
        info_header.addWidget(QLabel("Metadata"))
        info_header.addWidget(
            self._help_button(
                "Parsed metadata for the selected image. Fields are deduped and labeled."
            )
        )
        info_header.addStretch(1)
        info_layout.addLayout(info_header)
        info_layout.addWidget(self.info_window)

        detail_splitter.addWidget(preview_panel)
        detail_splitter.addWidget(info_panel)
        self._init_splitter(detail_splitter, "gallery/details", [600, 240])

        side_layout.addWidget(detail_splitter)
        side_panel.setLayout(side_layout)
        side_scroll = QScrollArea()  # DIFF-001-004
        side_scroll.setWidgetResizable(True)  # DIFF-001-004
        side_scroll.setFrameShape(QFrame.NoFrame)  # DIFF-001-004
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # DIFF-001-004
        side_scroll.setWidget(side_panel)  # DIFF-001-004
        side_scroll.setMinimumWidth(320)  # DIFF-001-003
        splitter.addWidget(side_scroll)  # DIFF-001-004

        self._init_splitter(splitter, "gallery/main", [900, 320])  # DIFF-001-005
        splitter.setStretchFactor(0, 3)  # DIFF-001-005
        splitter.setStretchFactor(1, 1)  # DIFF-001-005
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # Load all records for filtering
        self.csv_path = str(resolve_repo_path("out/records.csv", must_exist=False, allow_absolute=False))
        self.all_records = load_records(self.csv_path)
        self.filtered_records = self.all_records
        self.selected_images = []
        self.csv_columns = self._compute_csv_columns(self.all_records)
        self.thumb_cache = {}
        self.selected_tags = set()
        self._ui_settings = load_ui_settings()
        self._build_tag_menu()
        self._load_display_settings()
        self.update_grid()

        self.thumb_size_slider.valueChanged.connect(self._on_thumb_size_changed)
        self.thumb_spacing_slider.valueChanged.connect(self._on_thumb_spacing_changed)

    def _help_button(self, text):
        btn = QToolButton()
        btn.setText("?")
        btn.setAutoRaise(True)
        btn.setToolTip(text)
        btn.setCursor(Qt.WhatsThisCursor)
        btn.setFixedSize(16, 16)
        return btn

    def _apply_page_layout(self, layout: QHBoxLayout) -> None:
        layout.setContentsMargins(UI_OUTER_PADDING, UI_OUTER_PADDING, UI_OUTER_PADDING, UI_OUTER_PADDING)  # DIFF-001-001
        layout.setSpacing(UI_SECTION_GAP)  # DIFF-001-001

    def _apply_section_layout(self, layout: QVBoxLayout) -> None:
        layout.setContentsMargins(UI_SECTION_GAP, UI_SECTION_GAP, UI_SECTION_GAP, UI_SECTION_GAP)  # DIFF-001-001
        layout.setSpacing(UI_INNER_GAP)  # DIFF-001-001

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

    def _compute_csv_columns(self, records):
        extra = sorted({k for r in records for k in r.keys() if not k.startswith("_")} - set(CSV_COLUMNS))
        return CSV_COLUMNS + extra

    def _record_key(self, rec):
        return rec.get("source_file") or rec.get("file_name") or ""

    def _record_image_path(self, rec):
        cached = rec.get("_image_path")
        if isinstance(cached, str) and cached:
            return cached
        name = rec.get("file_name")
        if isinstance(name, str) and name:
            return str(resolve_repo_path(os.path.join("Input", name), must_exist=False, allow_absolute=False))
        src = rec.get("source_file")
        if isinstance(src, str) and src:
            return str(resolve_repo_path(os.path.join("Input", os.path.basename(src)), must_exist=False, allow_absolute=False))
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
        thumb = self._thumbnail_path_for_record(rec)
        if not img_path or not os.path.exists(img_path):
            if not os.path.exists(thumb):
                thumb = ""
        self.thumb_cache[key] = thumb
        return thumb

    def reload_records(self):
        self.all_records = load_records(self.csv_path)
        self.filtered_records = self.all_records
        self.thumb_cache = {}
        self._build_tag_menu()
        self.update_grid()

    def _build_tag_menu(self):
        self.tag_list.blockSignals(True)
        self.tag_list.clear()
        tags = set()
        for rec in self.all_records:
            prompt_tags = rec.get("_prompt_tags") or set()
            tags.update(prompt_tags)
        for tag in sorted(tags):
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if tag in self.selected_tags else Qt.Unchecked)
            self.tag_list.addItem(item)
        self.tag_list.blockSignals(False)

    def _on_tag_item_changed(self, item):
        tag = item.text()
        if item.checkState() == Qt.Checked:
            self.selected_tags.add(tag)
        else:
            self.selected_tags.discard(tag)
        self.apply_tag_filter()
    def apply_sort(self):
        key = self.sort_combo.currentData()
        if not key:
            return
        numeric_keys = {"width", "height", "steps", "cfg_scale", "seed"}
        def tag_count(rec):
            return len([t for t in rec.get("prompt", "").split(",") if t.strip()])
        if key == "tag_count":
            self.filtered_records = sorted(self.filtered_records, key=tag_count, reverse=True)
        elif key in numeric_keys:
            self.filtered_records = sorted(
                self.filtered_records,
                key=lambda r: float(r.get(key) or 0),
                reverse=False,
            )
        else:
            self.filtered_records = sorted(self.filtered_records, key=lambda r: r.get(key, ""))
        self.update_grid()

    def update_grid(self):
        thumbs = []
        images = []
        for rec in self.filtered_records:
            if rec.get("_missing_original"):
                continue
            img_path = self._record_image_path(rec)
            if not img_path:
                continue
            if not os.path.exists(img_path):
                rec["_missing_original"] = True
                continue
            thumb_path = self._thumb_for_record(rec)
            if not thumb_path or not os.path.exists(thumb_path):
                continue
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
        tags = sorted(self.selected_tags)
        self.filtered_records = filter_by_tags(self.all_records, tags)
        self.update_grid()

    def on_images_selected(self, image_paths):
        self.selected_images = image_paths

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
            lines = []
            for k, v in rec.items():
                if k.startswith("_"):
                    continue
                key = html.escape(str(k).replace("_", " ").title())
                val = html.escape(str(v))
                val = val.replace("\n", "<br>")
                lines.append(
                    f"<div><span style='font-weight:700; font-size:11pt;'>{key}:</span> "
                    f"<span style='font-size:10pt;'>{val}</span></div>"
                )
            info = "<div style='line-height:1.25;'>" + "".join(lines) + "</div>"
            self.info_window.setHtml(info)
        else:
            info = f"Image Path: {img_path}\nThumbnail Path: {thumb_path}"
            self.info_window.setPlainText(info)

    def _load_display_settings(self) -> None:
        self._ui_settings = load_ui_settings()
        size = self._ui_settings.get("thumb_size", DEFAULT_THUMB_SIZE)
        spacing = self._ui_settings.get("thumb_spacing", DEFAULT_THUMB_SPACING)
        self.thumb_size_slider.blockSignals(True)
        self.thumb_size_slider.setValue(size)
        self.thumb_size_value.setText(str(size))
        self.thumb_size_slider.blockSignals(False)
        self.thumb_spacing_slider.blockSignals(True)
        self.thumb_spacing_slider.setValue(spacing)
        self.thumb_spacing_value.setText(str(spacing))
        self.thumb_spacing_slider.blockSignals(False)
        self.grid.set_thumbnail_size(size)
        self.grid.set_spacing(spacing)

    def _save_display_setting(self, key: str, value: int) -> None:
        settings = load_ui_settings()
        settings[key] = int(value)
        save_ui_settings(settings)
        self._ui_settings = settings

    def _on_thumb_size_changed(self, value: int) -> None:
        self.thumb_size_value.setText(str(value))
        self.grid.set_thumbnail_size(value)
        self._save_display_setting("thumb_size", value)

    def _on_thumb_spacing_changed(self, value: int) -> None:
        self.thumb_spacing_value.setText(str(value))
        self.grid.set_spacing(value)
        self._save_display_setting("thumb_spacing", value)
