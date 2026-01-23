import html
import json
import os
import re
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGroupBox,
    QLabel,
    QHBoxLayout,
    QAbstractItemView,
    QGridLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QScrollArea,
    QFrame,
    QWidget,
    QSplitter,
)

from simage.utils.paths import resolve_repo_path
from .theme import UI_INNER_GAP, UI_OUTER_PADDING, UI_SECTION_GAP  # DIFF-001-001
from .theme import theme_color
from .theme import load_splitter_sizes, save_splitter_sizes


class EditTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.records_jsonl_path = str(resolve_repo_path("out/records.jsonl", must_exist=False, allow_absolute=False))
        self.selected_images: List[str] = []
        self.workflow_text_by_name: Dict[str, str] = {}
        self.workflow_obj_by_name: Dict[str, object] = {}
        self.record_by_name: Dict[str, Dict[str, object]] = {}
        self.last_find_text = ""
        self.last_find_match_case = False
        self.last_find_relax_values = True
        self._suspend_auto_find = False
        self._auto_find_active = False
        self.node_anchor: Optional[Dict[str, object]] = None
        self.active_workflow_name: Optional[str] = None
        self.current_nodes_by_id: Dict[int, Dict[str, object]] = {}
        self.current_widget_idx_map: Dict[str, Dict[str, int]] = {}
        self._edit_settings_snapshot: Dict[str, object] = {}

        layout = QVBoxLayout(self)
        self._apply_page_layout(layout)

        info_label = QLabel("Workflow tools: find and extract values across selected images.")
        info_label.setWordWrap(True)
        info_row = QHBoxLayout()
        info_row.addWidget(info_label)
        info_row.addWidget(
            self._help_button("Use the Gallery tab to select images, then work here.")
        )
        info_row.addStretch(1)
        layout.addLayout(info_row)

        instructions = QLabel(
            "Step 1: Select images in Gallery. Step 2: Pick an image to load its workflow. "
            "Step 3: Use Anchor by Node or Find Text."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find in workflows (uses selection if any)")
        self.find_btn = QPushButton("Find Occurrences")
        self.find_btn.clicked.connect(self.find_occurrences)

        self.match_case_check = QCheckBox("Match case")
        self.relax_values_check = QCheckBox("Relax values")
        self.relax_values_check.setChecked(True)
        self.auto_find_check = QCheckBox("Auto find on selection")
        self.auto_find_check.setChecked(True)

        self.include_bypassed_check = QCheckBox("Include bypassed nodes")
        self.include_bypassed_check.setChecked(False)
        self.include_bypassed_check.stateChanged.connect(self._refresh_node_list)
        self.set_anchor_btn = QPushButton("Set Anchor")
        self.set_anchor_btn.clicked.connect(self.set_node_anchor)
        self.find_anchor_btn = QPushButton("Find Values")
        self.find_anchor_btn.clicked.connect(self.find_node_anchor_values)
        self.anchor_status_label = QLabel("Anchor: none")

        self.selected_list = QListWidget()
        self.selected_list.setMinimumHeight(0)
        self.selected_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.selected_list.itemSelectionChanged.connect(self._on_selected_item_changed)

        self.node_list = QListWidget()
        self.node_list.setMinimumHeight(0)
        self.node_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.node_list.itemSelectionChanged.connect(self._on_node_selected)

        self.field_list = QListWidget()
        self.field_list.setMinimumHeight(0)
        self.field_list.setSelectionMode(QAbstractItemView.SingleSelection)

        self.find_results = QListWidget()
        self.find_results.setMinimumHeight(0)
        self.find_results.itemSelectionChanged.connect(self._on_result_selected)

        self.anchor_results = QListWidget()
        self.anchor_results.setMinimumHeight(0)
        self.anchor_results.itemSelectionChanged.connect(self._on_anchor_result_selected)

        self.workflow_view = QTextEdit()
        self.workflow_view.setReadOnly(True)
        self.workflow_view.selectionChanged.connect(self._on_workflow_selection_changed)

        main_splitter = QSplitter(Qt.Horizontal)

        selected_panel = QGroupBox("Selected Images")
        selected_layout = QVBoxLayout(selected_panel)
        self._apply_section_layout(selected_layout)
        selected_header = QHBoxLayout()
        self.selected_label = QLabel("Selected: 0")
        selected_header.addWidget(self.selected_label)
        selected_header.addStretch(1)
        selected_header.addWidget(
            self._help_button("Shows how many images are currently selected.")
        )
        selected_layout.addLayout(selected_header)
        selected_layout.addWidget(QLabel("Click an image to load its workflow."))
        selected_layout.addWidget(self.selected_list)

        matches_panel = QGroupBox("Find Text")
        matches_layout = QVBoxLayout(matches_panel)
        self._apply_section_layout(matches_layout)
        matches_help = QHBoxLayout()
        matches_help.addStretch(1)
        matches_help.addWidget(
            self._help_button("Select text in Workflow and it will find matches (if enabled).")
        )
        matches_layout.addLayout(matches_help)
        find_row = QHBoxLayout()
        find_row.addWidget(self.find_input)
        find_row.addWidget(self.find_btn)
        find_row.addWidget(self._help_button("Find matching text in workflows."))
        find_row.addStretch(1)
        matches_layout.addLayout(find_row)
        find_opts = QHBoxLayout()
        find_opts.addWidget(self.match_case_check)
        find_opts.addWidget(self.relax_values_check)
        find_opts.addWidget(self.auto_find_check)
        find_opts.addWidget(
            self._help_button("Relax values ignores string/number differences in the selection.")
        )
        find_opts.addStretch(1)
        matches_layout.addLayout(find_opts)
        matches_layout.addWidget(QLabel("Matches"))
        matches_layout.addWidget(self.find_results)

        anchor_panel = QGroupBox("Anchor by Node")
        anchor_layout = QVBoxLayout(anchor_panel)
        self._apply_section_layout(anchor_layout)
        anchor_help = QHBoxLayout()
        anchor_help.addStretch(1)
        anchor_help.addWidget(
            self._help_button("Pick a node and field from the current workflow.")
        )
        anchor_layout.addLayout(anchor_help)
        anchor_layout.addWidget(QLabel("Choose a node, then a field to anchor."))

        node_row = QHBoxLayout()
        node_row.addWidget(QLabel("Nodes"))
        node_row.addWidget(self.include_bypassed_check)
        node_row.addStretch(1)
        anchor_layout.addLayout(node_row)
        anchor_layout.addWidget(self.node_list)

        anchor_layout.addWidget(QLabel("Fields"))
        anchor_layout.addWidget(self.field_list)

        anchor_actions = QHBoxLayout()
        anchor_actions.addWidget(self.set_anchor_btn)
        anchor_actions.addWidget(self.find_anchor_btn)
        anchor_actions.addWidget(
            self._help_button("Anchor uses node id and field index from the workflow.")
        )
        anchor_actions.addStretch(1)
        anchor_layout.addLayout(anchor_actions)
        anchor_layout.addWidget(self.anchor_status_label)
        anchor_layout.addWidget(QLabel("Anchor Results"))
        anchor_layout.addWidget(self.anchor_results)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(UI_SECTION_GAP)  # DIFF-001-001
        left_layout.addWidget(selected_panel)
        left_layout.addWidget(anchor_panel)
        left_layout.addWidget(matches_panel)
        left_layout.addStretch(1)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setWidget(left_container)
        left_scroll.setMinimumWidth(240)  # DIFF-001-003

        workflow_panel = QGroupBox("Workflow")
        workflow_panel.setMinimumWidth(480)  # DIFF-001-003
        workflow_layout = QVBoxLayout(workflow_panel)
        self._apply_section_layout(workflow_layout)
        workflow_help = QHBoxLayout()
        workflow_help.addStretch(1)
        workflow_help.addWidget(
            self._help_button("Select text here to find matching sections across images.")
        )
        workflow_layout.addLayout(workflow_help)
        workflow_layout.addWidget(self.workflow_view)

        main_splitter.addWidget(left_scroll)
        main_splitter.addWidget(workflow_panel)
        main_splitter.setStretchFactor(0, 1)  # DIFF-001-005
        main_splitter.setStretchFactor(1, 3)  # DIFF-001-005
        self._init_splitter(main_splitter, "edit/main", [360, 840])

        file_actions_panel = QGroupBox("File Actions")
        file_actions_layout = QVBoxLayout(file_actions_panel)
        self._apply_section_layout(file_actions_layout)
        file_help = QHBoxLayout()
        file_help.addStretch(1)
        file_help.addWidget(
            self._help_button("Strip embedded metadata so files can be reparsed.")
        )
        file_actions_layout.addLayout(file_help)

        options_row = QHBoxLayout()
        self.keep_backup_check = QCheckBox("Keep backup (.original)")
        self.keep_backup_check.setChecked(True)
        options_row.addWidget(self.keep_backup_check)
        options_row.addWidget(
            self._help_button("ExifTool keeps a .original backup by default.")
        )
        options_row.addStretch(1)
        file_actions_layout.addLayout(options_row)

        actions_row = QHBoxLayout()
        self.strip_btn = QPushButton("Strip Embedded Metadata (Reparse)")
        self.strip_btn.clicked.connect(self.remove_metadata)
        actions_row.addWidget(self.strip_btn)
        actions_row.addWidget(
            self._help_button("Remove all metadata from the selected images.")
        )
        actions_row.addStretch(1)
        file_actions_layout.addLayout(actions_row)

        self.edit_prompt = QTextEdit()
        self.edit_negative_prompt = QTextEdit()
        self.edit_model = QLineEdit()
        self.edit_sampler = QLineEdit()
        self.edit_scheduler = QLineEdit()
        self.edit_steps = QLineEdit()
        self.edit_cfg_scale = QLineEdit()
        self.edit_seed = QLineEdit()
        self._edit_fields = [
            self.edit_prompt,
            self.edit_negative_prompt,
            self.edit_model,
            self.edit_sampler,
            self.edit_scheduler,
            self.edit_steps,
            self.edit_cfg_scale,
            self.edit_seed,
        ]

        edit_settings_panel = QGroupBox("Edit Settings")
        edit_settings_layout = QVBoxLayout(edit_settings_panel)
        self._apply_section_layout(edit_settings_layout)
        edit_help = QHBoxLayout()
        edit_help.addStretch(1)
        edit_help.addWidget(
            self._help_button("Update key metadata fields in records.jsonl.")
        )
        edit_settings_layout.addLayout(edit_help)
        self.edit_active_label = QLabel("Editing: none")
        edit_settings_layout.addWidget(self.edit_active_label)

        edit_settings_layout.addWidget(QLabel("Prompt"))
        edit_settings_layout.addWidget(self.edit_prompt)
        edit_settings_layout.addWidget(QLabel("Negative Prompt"))
        edit_settings_layout.addWidget(self.edit_negative_prompt)

        fields_grid = QGridLayout()
        fields_grid.addWidget(QLabel("Model"), 0, 0)
        fields_grid.addWidget(self.edit_model, 0, 1)
        fields_grid.addWidget(QLabel("Sampler"), 1, 0)
        fields_grid.addWidget(self.edit_sampler, 1, 1)
        fields_grid.addWidget(QLabel("Scheduler"), 2, 0)
        fields_grid.addWidget(self.edit_scheduler, 2, 1)
        fields_grid.addWidget(QLabel("Steps"), 0, 2)
        fields_grid.addWidget(self.edit_steps, 0, 3)
        fields_grid.addWidget(QLabel("CFG Scale"), 1, 2)
        fields_grid.addWidget(self.edit_cfg_scale, 1, 3)
        fields_grid.addWidget(QLabel("Seed"), 2, 2)
        fields_grid.addWidget(self.edit_seed, 2, 3)
        edit_settings_layout.addLayout(fields_grid)

        edit_actions = QHBoxLayout()
        self.save_settings_btn = QPushButton("Save to current image")
        self.save_settings_btn.clicked.connect(self.save_current_settings)
        self.save_all_settings_btn = QPushButton("Apply to all selected images")
        self.save_all_settings_btn.clicked.connect(self.save_all_settings)
        self.reset_settings_btn = QPushButton("Reload current image")
        self.reset_settings_btn.clicked.connect(self.reload_edit_fields)
        edit_actions.addWidget(self.save_settings_btn)
        edit_actions.addWidget(self.save_all_settings_btn)
        edit_actions.addWidget(self.reset_settings_btn)
        edit_actions.addStretch(1)
        edit_settings_layout.addLayout(edit_actions)
        edit_settings_layout.addStretch(1)

        details_panel = QGroupBox("Image Details")
        details_layout = QVBoxLayout(details_panel)
        self._apply_section_layout(details_layout)
        details_help = QHBoxLayout()
        details_help.addStretch(1)
        details_help.addWidget(
            self._help_button("Metadata loaded from records.jsonl and workflow JSON.")
        )
        details_layout.addLayout(details_help)
        self.details_name_label = QLabel("Image: none")
        details_layout.addWidget(self.details_name_label)
        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("IP Address"))
        self.ip_value_label = QLabel("Not found")
        ip_row.addWidget(self.ip_value_label)
        ip_row.addStretch(1)
        details_layout.addLayout(ip_row)

        details_splitter = QSplitter(Qt.Vertical)
        summary_panel = QWidget()
        summary_layout = QVBoxLayout(summary_panel)
        self._apply_section_layout(summary_layout)
        summary_layout.addWidget(QLabel("Summary"))
        self.summary_view = QTextEdit()
        self.summary_view.setReadOnly(True)
        summary_layout.addWidget(self.summary_view)
        details_splitter.addWidget(summary_panel)

        kv_panel = QWidget()
        kv_layout = QVBoxLayout(kv_panel)
        self._apply_section_layout(kv_layout)
        kv_layout.addWidget(QLabel("Key/Value Metadata"))
        self.kv_view = QTextEdit()
        self.kv_view.setReadOnly(True)
        kv_layout.addWidget(self.kv_view)
        details_splitter.addWidget(kv_panel)

        raw_panel = QWidget()
        raw_layout = QVBoxLayout(raw_panel)
        self._apply_section_layout(raw_layout)
        raw_layout.addWidget(QLabel("Raw Text Preview"))
        self.raw_view = QTextEdit()
        self.raw_view.setReadOnly(True)
        raw_layout.addWidget(self.raw_view)
        details_splitter.addWidget(raw_panel)
        self._init_splitter(details_splitter, "edit/details", [220, 220, 180])

        details_layout.addWidget(details_splitter)

        workflow_tab = QWidget()
        workflow_layout = QVBoxLayout(workflow_tab)
        workflow_layout.addWidget(main_splitter)
        workflow_layout.addStretch(1)

        file_actions_tab = QWidget()
        file_actions_tab_layout = QVBoxLayout(file_actions_tab)
        file_actions_tab_layout.addWidget(file_actions_panel)
        file_actions_tab_layout.addStretch(1)

        self.tabs = QTabWidget()
        self.tabs.addTab(workflow_tab, "Workflow Tools")
        self.tabs.addTab(edit_settings_panel, "Edit Settings")
        self.tabs.addTab(details_panel, "Image Details")
        self.tabs.addTab(file_actions_tab, "File Actions")
        layout.addWidget(self.tabs)
        self._clear_details()
        self._clear_edit_fields()

    def _help_button(self, text):
        btn = QToolButton()
        btn.setText("?")
        btn.setAutoRaise(True)
        btn.setToolTip(text)
        btn.setCursor(Qt.WhatsThisCursor)
        btn.setFixedSize(16, 16)
        return btn

    def _apply_page_layout(self, layout: QVBoxLayout) -> None:
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

    def set_selected_images(self, image_paths: List[str]) -> None:
        self.selected_images = image_paths
        self.selected_label.setText(f"Selected: {len(image_paths)}")
        self.selected_list.clear()
        for path in image_paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            self.selected_list.addItem(item)
        self._reload_workflows()

    def _reload_workflows(self) -> None:
        names = self._selected_names()
        self.workflow_text_by_name = self._load_workflows_for_names(names)
        self.find_results.clear()
        self.anchor_results.clear()
        if names:
            first = self.selected_list.item(0)
            if first:
                first.setSelected(True)
                self._show_workflow_for_name(first.text())
        else:
            self._set_workflow_text("No image selected.")
            self._clear_highlights()
            self.active_workflow_name = None
            self._clear_details()
            self._clear_edit_fields()

    def _ensure_selection(self) -> bool:
        if self.selected_images:
            return True
        QMessageBox.warning(self, "No Selection", "Select images in the Gallery tab first.")
        return False

    def _find_exiftool(self) -> Path | None:
        candidates = [
            resolve_repo_path("exiftool-13.45_64/ExifTool.exe", must_exist=False, allow_absolute=False),
            resolve_repo_path("exiftool-13.45_64/exiftool", must_exist=False, allow_absolute=False),
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _selected_names(self) -> List[str]:
        names = []
        for path in self.selected_images:
            if path:
                names.append(os.path.basename(path))
        return names

    def _load_workflows_for_names(self, names: List[str]) -> Dict[str, str]:
        self.workflow_obj_by_name = {}
        self.record_by_name = {}
        if not names or not os.path.exists(self.records_jsonl_path):
            return {}
        target = set(names)
        out: Dict[str, str] = {}
        with open(self.records_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                name = rec.get("file_name")
                if name not in target:
                    continue
                wf = rec.get("workflow_json")
                if wf is None:
                    wf = rec.get("kv", {}).get("workflow_json")
                self.workflow_obj_by_name[name] = self._normalize_workflow_obj(wf)
                out[name] = self._format_workflow(wf)
                self.record_by_name[name] = rec
                target.discard(name)
                if not target:
                    break
        return out

    def _normalize_workflow_obj(self, wf: Optional[object]) -> Optional[object]:
        if wf is None:
            return None
        if isinstance(wf, (dict, list)):
            return wf
        if isinstance(wf, str):
            wf_str = wf.strip()
            if not wf_str:
                return None
            if wf_str.startswith("{") or wf_str.startswith("["):
                try:
                    return json.loads(wf_str)
                except Exception:
                    return None
        return None

    def _format_workflow(self, wf: Optional[object]) -> str:
        if wf is None:
            return ""
        if isinstance(wf, str):
            wf_str = wf.strip()
            if not wf_str:
                return ""
            if wf_str.startswith("{") or wf_str.startswith("["):
                try:
                    parsed = json.loads(wf_str)
                except Exception:
                    return wf_str
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            return wf_str
        try:
            return json.dumps(wf, indent=2, ensure_ascii=False)
        except Exception:
            return str(wf)

    def _set_workflow_text(self, text: str) -> None:
        self._suspend_auto_find = True
        self.workflow_view.setPlainText(text)
        self._suspend_auto_find = False

    def _show_workflow_for_name(self, name: str, highlight_span: Optional[tuple[int, int]] = None) -> None:
        self.active_workflow_name = name
        text = self.workflow_text_by_name.get(name, "")
        if not text:
            if not os.path.exists(self.records_jsonl_path):
                self._set_workflow_text("records.jsonl not found. Run the pipeline to generate workflows.")
            else:
                self._set_workflow_text("No workflow JSON found for this image.")
            self._clear_highlights()
            self._refresh_node_list()
            self._refresh_details_for_name(name)
            self._refresh_edit_fields_for_name(name)
            return
        self._set_workflow_text(text)
        if highlight_span:
            self._highlight_span(highlight_span[0], highlight_span[1])
        else:
            self._highlight_matches(self.last_find_text, self.last_find_match_case, self.last_find_relax_values)
            self._focus_first_match(self.last_find_text, self.last_find_match_case)
        self._refresh_node_list()
        self._refresh_details_for_name(name)
        self._refresh_edit_fields_for_name(name)

    def _on_selected_item_changed(self) -> None:
        items = self.selected_list.selectedItems()
        if not items:
            return
        name = items[0].text()
        self._show_workflow_for_name(name)

    def _on_result_selected(self) -> None:
        items = self.find_results.selectedItems()
        if not items:
            return
        name = items[0].data(Qt.UserRole) or items[0].text().split(" (", 1)[0]
        for i in range(self.selected_list.count()):
            item = self.selected_list.item(i)
            if item.text() == name:
                item.setSelected(True)
                self.selected_list.scrollToItem(item)
                break
        self._show_workflow_for_name(name)

    def _on_anchor_result_selected(self) -> None:
        items = self.anchor_results.selectedItems()
        if not items:
            return
        data = items[0].data(Qt.UserRole) or {}
        name = data.get("name") or items[0].text().split(":", 1)[0].strip()
        for i in range(self.selected_list.count()):
            item = self.selected_list.item(i)
            if item.text() == name:
                item.setSelected(True)
                self.selected_list.scrollToItem(item)
                break
        self._show_workflow_for_name(name)

    def _on_node_selected(self) -> None:
        items = self.node_list.selectedItems()
        if not items:
            self.field_list.clear()
            return
        data = items[0].data(Qt.UserRole) or {}
        node_id = data.get("node_id")
        if node_id is None:
            self.field_list.clear()
            return
        node = self.current_nodes_by_id.get(int(node_id))
        if not node:
            self.field_list.clear()
            return
        self._populate_field_list(node)

    def _refresh_node_list(self) -> None:
        self.node_list.clear()
        self.field_list.clear()
        self.current_nodes_by_id = {}
        self.current_widget_idx_map = {}
        name = self.active_workflow_name
        if not name:
            return
        workflow = self.workflow_obj_by_name.get(name)
        if not workflow:
            return
        nodes = self._workflow_nodes(workflow)
        if not nodes:
            return
        self.current_widget_idx_map = self._widget_idx_map(workflow)
        include_bypassed = self.include_bypassed_check.isChecked()
        nodes_sorted = sorted(nodes, key=lambda n: n.get("order", 0))
        for node in nodes_sorted:
            node_id = node.get("id")
            if node_id is None:
                continue
            try:
                node_id_int = int(node_id)
            except Exception:
                continue
            if not include_bypassed and self._node_is_bypassed(node):
                continue
            label = self._node_label(node)
            if self._node_is_bypassed(node):
                label = f"{label} (bypassed)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, {"node_id": node_id_int})
            self.node_list.addItem(item)
            self.current_nodes_by_id[node_id_int] = node
        if self.node_list.count() > 0:
            self.node_list.item(0).setSelected(True)

    def _workflow_nodes(self, workflow: object) -> List[Dict[str, object]]:
        if isinstance(workflow, dict):
            nodes = workflow.get("nodes")
            if isinstance(nodes, list):
                return [n for n in nodes if isinstance(n, dict)]
        if isinstance(workflow, list):
            return [n for n in workflow if isinstance(n, dict)]
        return []

    def _widget_idx_map(self, workflow: object) -> Dict[str, Dict[str, int]]:
        if isinstance(workflow, dict):
            raw = workflow.get("widget_idx_map")
            if isinstance(raw, dict):
                out: Dict[str, Dict[str, int]] = {}
                for node_id, mapping in raw.items():
                    if isinstance(mapping, dict):
                        clean = {str(k): int(v) for k, v in mapping.items() if isinstance(v, int)}
                        out[str(node_id)] = clean
                return out
        return {}

    def _node_is_bypassed(self, node: Dict[str, object]) -> bool:
        mode = node.get("mode")
        return isinstance(mode, int) and mode != 0

    def _node_title(self, node: Dict[str, object]) -> str:
        title = node.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
        props = node.get("properties") if isinstance(node.get("properties"), dict) else {}
        name = props.get("Node name for S&R") if isinstance(props, dict) else None
        if isinstance(name, str) and name.strip():
            return name.strip()
        return ""

    def _node_label(self, node: Dict[str, object]) -> str:
        node_id = node.get("id")
        node_type = node.get("type") or node.get("class_type") or "Node"
        title = self._node_title(node)
        if title and title != node_type:
            return f"{node_id} | {node_type} | {title}"
        return f"{node_id} | {node_type}"

    def _populate_field_list(self, node: Dict[str, object]) -> None:
        self.field_list.clear()
        node_id = node.get("id")
        widgets = node.get("widgets_values")
        if not isinstance(widgets, list):
            widgets = []
        idx_map = self.current_widget_idx_map.get(str(node_id), {})
        if idx_map:
            items = []
            for name, idx in idx_map.items():
                if 0 <= idx < len(widgets):
                    value = widgets[idx]
                    items.append((name, idx, value))
            items.sort(key=lambda x: x[1])
            for name, idx, value in items:
                label = f"{name} = {self._format_field_value(value)}"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, {"field_name": name, "field_index": idx})
                self.field_list.addItem(item)
        else:
            for idx, value in enumerate(widgets):
                label = f"value[{idx}] = {self._format_field_value(value)}"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, {"field_name": f"value[{idx}]", "field_index": idx})
                self.field_list.addItem(item)

    def _format_field_value(self, value: object) -> str:
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, str):
            s = value.replace("\n", " ").strip()
            return s if len(s) <= 80 else f"{s[:77]}..."
        if isinstance(value, (dict, list)):
            try:
                s = json.dumps(value, ensure_ascii=False)
            except Exception:
                s = str(value)
            return s if len(s) <= 80 else f"{s[:77]}..."
        return str(value)

    def _clear_details(self) -> None:
        self.details_name_label.setText("Image: none")
        self.ip_value_label.setText("Not found")
        self.summary_view.setPlainText("No details loaded.")
        self.kv_view.setPlainText("")
        self.raw_view.setPlainText("")

    def _refresh_details_for_name(self, name: str) -> None:
        rec = self.record_by_name.get(name)
        if not rec:
            self._clear_details()
            return
        self.details_name_label.setText(f"Image: {name}")
        ip, source = self._extract_ip(rec)
        if ip:
            self.ip_value_label.setText(f"{ip} ({source})")
        else:
            self.ip_value_label.setText("Not found")

        self.summary_view.setHtml(self._build_summary(rec, name))
        kv = rec.get("kv")
        if isinstance(kv, dict) and kv:
            self.kv_view.setPlainText(json.dumps(kv, indent=2, ensure_ascii=False))
        else:
            self.kv_view.setPlainText("No key/value metadata found.")

        raw = rec.get("raw_text_preview")
        if isinstance(raw, str) and raw.strip():
            self.raw_view.setPlainText(raw)
        else:
            self.raw_view.setPlainText("No raw text preview.")

    def _build_summary(self, rec: Dict[str, object], name: str) -> str:
        lines = []

        def add(label: str, value: object) -> None:
            if value in (None, ""):
                return
            lines.append(
                f"<div><span style='font-weight:700;'>{html.escape(label)}:</span> "
                f"{html.escape(str(value))}</div>"
            )

        dims = None
        width = rec.get("width")
        height = rec.get("height")
        if width or height:
            dims = f"{width} x {height}"

        add("File", rec.get("file_name") or name)
        add("Source", rec.get("source_file"))
        add("Format", rec.get("format_hint"))
        add("Dimensions", dims)
        add("Created UTC", rec.get("created_utc"))
        add("Imported UTC", rec.get("imported_utc"))
        add("SHA256", rec.get("sha256"))
        add("Model", rec.get("model"))
        add("Sampler", rec.get("sampler"))
        add("Scheduler", rec.get("scheduler"))
        add("Steps", rec.get("steps"))
        add("CFG Scale", rec.get("cfg_scale"))
        add("Seed", rec.get("seed"))

        kv = rec.get("kv") if isinstance(rec.get("kv"), dict) else {}
        prompt = rec.get("prompt") or kv.get("prompt_text") or kv.get("prompt")
        neg = rec.get("negative_prompt") or kv.get("neg_prompt_text") or kv.get("negative_prompt")
        add("Prompt", self._truncate_text(prompt))
        add("Negative Prompt", self._truncate_text(neg))

        resources = rec.get("resources")
        if isinstance(resources, list) and resources:
            resource_lines = []
            for res in resources:
                if not isinstance(res, dict):
                    continue
                kind = res.get("kind") or "resource"
                name_val = res.get("name") or "unknown"
                resource_lines.append(f"{kind}: {name_val}")
            if resource_lines:
                add("Resources", "; ".join(resource_lines))

        wf = self.workflow_obj_by_name.get(name)
        nodes = self._workflow_nodes(wf) if wf else []
        if nodes:
            bypassed = sum(1 for n in nodes if self._node_is_bypassed(n))
            add("Workflow nodes", len(nodes))
            add("Bypassed nodes", bypassed)

        if not lines:
            return "<div>No details loaded.</div>"
        return "<div style='line-height:1.35;'>" + "".join(lines) + "</div>"

    def _truncate_text(self, value: object, max_len: int = 180) -> str:
        if value in (None, ""):
            return ""
        text = str(value).replace("\n", " ").strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    def _extract_ip(self, rec: Dict[str, object]) -> tuple[str, str]:
        key_candidates = (
            "ip",
            "ip_address",
            "ip_addr",
            "client_ip",
            "remote_ip",
            "source_ip",
            "ipv4",
        )
        for key in key_candidates:
            val = rec.get(key)
            if isinstance(val, str):
                ip = self._find_ip_in_text(val)
                if ip:
                    return ip, f"record.{key}"

        kv = rec.get("kv")
        if isinstance(kv, dict):
            for k, v in kv.items():
                if "ip" in str(k).lower():
                    ip = self._find_ip_in_text(str(v))
                    if ip:
                        return ip, f"kv.{k}"
            for v in kv.values():
                if isinstance(v, str):
                    ip = self._find_ip_in_text(v)
                    if ip:
                        return ip, "kv"

        raw = rec.get("raw_text_preview")
        if isinstance(raw, str):
            ip = self._find_ip_in_text(raw)
            if ip:
                return ip, "raw_text_preview"

        wf = rec.get("workflow_json")
        if wf is not None:
            if isinstance(wf, str):
                text = wf
            else:
                try:
                    text = json.dumps(wf, ensure_ascii=False)
                except Exception:
                    text = str(wf)
            ip = self._find_ip_in_text(text)
            if ip:
                return ip, "workflow_json"

        return "", ""

    def _find_ip_in_text(self, text: str) -> str:
        if not text:
            return ""
        matches = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
        for match in matches:
            if self._valid_ip(match):
                return match
        return ""

    def _valid_ip(self, ip: str) -> bool:
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except Exception:
            return False

    def _clear_edit_fields(self) -> None:
        self._edit_settings_snapshot = {}
        self.edit_active_label.setText("Editing: none")
        self.edit_prompt.setPlainText("")
        self.edit_negative_prompt.setPlainText("")
        self.edit_model.clear()
        self.edit_sampler.clear()
        self.edit_scheduler.clear()
        self.edit_steps.clear()
        self.edit_cfg_scale.clear()
        self.edit_seed.clear()
        self._set_edit_enabled(False)

    def _set_edit_enabled(self, enabled: bool) -> None:
        for widget in self._edit_fields:
            widget.setEnabled(enabled)
        self.save_settings_btn.setEnabled(enabled)
        self.save_all_settings_btn.setEnabled(enabled)
        self.reset_settings_btn.setEnabled(enabled)

    def _refresh_edit_fields_for_name(self, name: str) -> None:
        rec = self.record_by_name.get(name)
        if not rec:
            self._clear_edit_fields()
            return
        self._set_edit_enabled(True)
        self.edit_active_label.setText(f"Editing: {name}")
        kv = rec.get("kv") if isinstance(rec.get("kv"), dict) else {}

        prompt = rec.get("prompt") or kv.get("prompt_text") or kv.get("prompt")
        neg = rec.get("negative_prompt") or kv.get("neg_prompt_text") or kv.get("negative_prompt")
        model = rec.get("model")
        sampler = rec.get("sampler")
        scheduler = rec.get("scheduler")
        steps = self._coerce_int(rec.get("steps"))
        cfg_scale = self._coerce_float(rec.get("cfg_scale"))
        seed = self._coerce_int(rec.get("seed"))

        self.edit_prompt.setPlainText("" if prompt is None else str(prompt))
        self.edit_negative_prompt.setPlainText("" if neg is None else str(neg))
        self.edit_model.setText("" if model is None else str(model))
        self.edit_sampler.setText("" if sampler is None else str(sampler))
        self.edit_scheduler.setText("" if scheduler is None else str(scheduler))
        self.edit_steps.setText("" if steps is None else str(steps))
        self.edit_cfg_scale.setText("" if cfg_scale is None else str(cfg_scale))
        self.edit_seed.setText("" if seed is None else str(seed))

        self._edit_settings_snapshot = {
            "prompt": prompt,
            "negative_prompt": neg,
            "model": model,
            "sampler": sampler,
            "scheduler": scheduler,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "seed": seed,
        }

    def reload_edit_fields(self) -> None:
        name = self.active_workflow_name
        if not name:
            self._clear_edit_fields()
            return
        self._refresh_edit_fields_for_name(name)

    def save_current_settings(self) -> None:
        self._save_settings(for_all=False)

    def save_all_settings(self) -> None:
        self._save_settings(for_all=True)

    def _save_settings(self, *, for_all: bool) -> None:
        if not self._ensure_selection():
            return
        if not self.active_workflow_name:
            QMessageBox.information(self, "Edit Settings", "Select an image first.")
            return
        changes = self._collect_edit_changes()
        if changes is None:
            return
        if not changes:
            QMessageBox.information(self, "Edit Settings", "No changes to save.")
            return

        targets = self._selected_names() if for_all else [self.active_workflow_name]
        updated = self._update_records_jsonl(targets, changes)
        if updated == 0:
            QMessageBox.information(self, "Edit Settings", "No records were updated.")
            return

        for name in targets:
            rec = self.record_by_name.get(name)
            if rec:
                self._apply_changes_to_record(rec, changes)

        self._refresh_details_for_name(self.active_workflow_name)
        self._refresh_edit_fields_for_name(self.active_workflow_name)
        QMessageBox.information(self, "Edit Settings", f"Updated {updated} record(s) in records.jsonl.")

    def _collect_edit_changes(self) -> Optional[Dict[str, object]]:
        errors = []

        prompt = self.edit_prompt.toPlainText().strip()
        neg = self.edit_negative_prompt.toPlainText().strip()
        model = self.edit_model.text().strip()
        sampler = self.edit_sampler.text().strip()
        scheduler = self.edit_scheduler.text().strip()

        steps, err = self._parse_int_field(self.edit_steps.text().strip(), "Steps")
        if err:
            errors.append(err)
        cfg_scale, err = self._parse_float_field(self.edit_cfg_scale.text().strip(), "CFG Scale")
        if err:
            errors.append(err)
        seed, err = self._parse_int_field(self.edit_seed.text().strip(), "Seed")
        if err:
            errors.append(err)

        if errors:
            QMessageBox.warning(self, "Edit Settings", "\n".join(errors))
            return None

        new_values = {
            "prompt": prompt or None,
            "negative_prompt": neg or None,
            "model": model or None,
            "sampler": sampler or None,
            "scheduler": scheduler or None,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "seed": seed,
        }

        changes = {}
        for key, new_value in new_values.items():
            if new_value != self._edit_settings_snapshot.get(key):
                changes[key] = new_value
        return changes

    def _parse_int_field(self, value: str, label: str) -> tuple[Optional[int], str | None]:
        if value == "":
            return None, None
        try:
            return int(value), None
        except Exception:
            return None, f"{label} must be an integer."

    def _parse_float_field(self, value: str, label: str) -> tuple[Optional[float], str | None]:
        if value == "":
            return None, None
        try:
            return float(value), None
        except Exception:
            return None, f"{label} must be a number."

    def _coerce_int(self, value: object) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        try:
            return int(str(value))
        except Exception:
            return None

    def _coerce_float(self, value: object) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)
        try:
            return float(str(value))
        except Exception:
            return None

    def _update_records_jsonl(self, names: List[str], changes: Dict[str, object]) -> int:
        if not os.path.exists(self.records_jsonl_path):
            QMessageBox.warning(
                self,
                "Edit Settings",
                "records.jsonl not found. Run the pipeline to generate workflows.",
            )
            return 0

        names_set = set(names)
        updated = 0
        output_lines: List[str] = []
        with open(self.records_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.rstrip("\n")
                if not raw.strip():
                    continue
                try:
                    rec = json.loads(raw)
                except Exception:
                    output_lines.append(raw)
                    continue
                if rec.get("file_name") in names_set:
                    self._apply_changes_to_record(rec, changes)
                    updated += 1
                output_lines.append(json.dumps(rec, ensure_ascii=False))

        if updated == 0:
            return 0

        backup_path = self.records_jsonl_path + ".bak"
        try:
            shutil.copy2(self.records_jsonl_path, backup_path)
        except Exception:
            pass

        with open(self.records_jsonl_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines) + "\n")
        return updated

    def _apply_changes_to_record(self, rec: Dict[str, object], changes: Dict[str, object]) -> None:
        for key, value in changes.items():
            rec[key] = value

        kv = rec.get("kv")
        if not isinstance(kv, dict):
            return

        if "prompt" in changes:
            if "prompt" in kv:
                kv["prompt"] = changes["prompt"]
            if "prompt_text" in kv:
                kv["prompt_text"] = changes["prompt"]
        if "negative_prompt" in changes:
            if "negative_prompt" in kv:
                kv["negative_prompt"] = changes["negative_prompt"]
            if "neg_prompt_text" in kv:
                kv["neg_prompt_text"] = changes["negative_prompt"]
        for key in ("model", "sampler", "scheduler", "steps", "cfg_scale", "seed"):
            if key in changes and key in kv:
                kv[key] = changes[key]

    def _on_workflow_selection_changed(self) -> None:
        if self._suspend_auto_find or not self.auto_find_check.isChecked():
            return
        text = self._selected_search_text(use_selection_only=True)
        if not text:
            return
        self.find_input.setText(text)
        self._auto_find_active = True
        try:
            self.find_occurrences()
        finally:
            self._auto_find_active = False

    def _selected_search_text(self, *, use_selection_only: bool = False) -> str:
        cursor = self.workflow_view.textCursor()
        selected = cursor.selectedText().replace("\u2029", "\n").strip()
        if selected:
            return selected
        if use_selection_only:
            return ""
        return self.find_input.text().strip()

    def _normalize_for_match(self, text: str, match_case: bool, relax_values: bool) -> str:
        if relax_values:
            text = re.sub(r"\"[^\"]*\"", "\"\"", text)
            text = re.sub(r"-?\d+(?:\.\d+)?", "0", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not match_case:
            text = text.lower()
        return text


    def find_occurrences(self) -> None:
        if not self._ensure_selection():
            return
        query = self._selected_search_text()
        if not query:
            QMessageBox.information(self, "Find", "Select text in Workflow or enter search text.")
            return

        match_case = self.match_case_check.isChecked()
        relax_values = self.relax_values_check.isChecked()
        self.last_find_text = query
        self.last_find_match_case = match_case
        self.last_find_relax_values = relax_values

        query_norm = self._normalize_for_match(query, match_case, relax_values)
        if not query_norm:
            QMessageBox.information(self, "Find", "Search text is empty after normalization.")
            return

        self.find_results.clear()
        matched = 0
        for name in self._selected_names():
            wf_text = self.workflow_text_by_name.get(name, "")
            if not wf_text:
                continue
            wf_norm = self._normalize_for_match(wf_text, match_case, relax_values)
            count = wf_norm.count(query_norm) if wf_norm else 0
            if count:
                item = QListWidgetItem(f"{name} ({count})")
                item.setData(Qt.UserRole, name)
                self.find_results.addItem(item)
                matched += 1

        if matched == 0 and not self._auto_find_active:
            QMessageBox.information(self, "Find", "No matches found in selected images.")

        current = self.selected_list.selectedItems()
        if current:
            if self._auto_find_active:
                self._highlight_matches(self.last_find_text, self.last_find_match_case, self.last_find_relax_values)
            else:
                self._show_workflow_for_name(current[0].text())

    def _clear_highlights(self) -> None:
        self.workflow_view.setExtraSelections([])

    def _highlight_span(self, start: int, end: int) -> None:
        if start < 0 or end <= start:
            self._clear_highlights()
            return
        text = self.workflow_view.toPlainText()
        if end > len(text):
            self._clear_highlights()
            return
        cursor = self.workflow_view.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        sel = QTextEdit.ExtraSelection()
        sel.cursor = cursor
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(theme_color("highlight", "#ffe08a")))
        sel.format = fmt
        self.workflow_view.setExtraSelections([sel])
        self.workflow_view.setTextCursor(cursor)

    def _highlight_matches(self, text: str, match_case: bool, relax_values: bool) -> None:
        if not text or relax_values:
            self._clear_highlights()
            return
        extra = []
        doc = self.workflow_view.document()
        cursor = QTextCursor(doc)
        flags = QTextDocument.FindCaseSensitively if match_case else QTextDocument.FindFlags()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(theme_color("highlight", "#ffe08a")))
        while True:
            cursor = doc.find(text, cursor, flags)
            if cursor.isNull():
                break
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            extra.append(sel)
        self.workflow_view.setExtraSelections(extra)

    def _focus_first_match(self, text: str, match_case: bool) -> None:
        if not text:
            return
        flags = QTextDocument.FindCaseSensitively if match_case else QTextDocument.FindFlags()
        cursor = self.workflow_view.document().find(text, 0, flags)
        if cursor and not cursor.isNull():
            self.workflow_view.setTextCursor(cursor)

    def set_node_anchor(self) -> None:
        node_items = self.node_list.selectedItems()
        field_items = self.field_list.selectedItems()
        if not node_items and self.node_list.count() > 0:
            self.node_list.item(0).setSelected(True)
            node_items = self.node_list.selectedItems()
        if not field_items and self.field_list.count() > 0:
            self.field_list.item(0).setSelected(True)
            field_items = self.field_list.selectedItems()
        if not node_items or not field_items:
            QMessageBox.information(self, "Anchor by Node", "Select a node and a field to anchor.")
            return
        node_data = node_items[0].data(Qt.UserRole) or {}
        field_data = field_items[0].data(Qt.UserRole) or {}
        node_id = node_data.get("node_id")
        field_index = field_data.get("field_index")
        field_name = field_data.get("field_name")
        if node_id is None or field_index is None:
            QMessageBox.information(self, "Anchor by Node", "Anchor selection is missing node or field info.")
            return
        node = self.current_nodes_by_id.get(int(node_id), {})
        node_type = node.get("type") or node.get("class_type") or "Node"
        node_title = self._node_title(node)
        self.node_anchor = {
            "node_id": int(node_id),
            "field_index": int(field_index),
            "field_name": str(field_name),
            "node_type": str(node_type),
            "node_title": str(node_title),
        }
        label = f"Anchor: node {node_id} / {field_name}"
        if node_title:
            label += f" ({node_title})"
        self.anchor_status_label.setText(label)

    def _find_node_for_anchor(
        self,
        workflow: object,
        anchor: Dict[str, object],
        *,
        include_bypassed: bool,
    ) -> tuple[Optional[Dict[str, object]], str]:
        nodes = self._workflow_nodes(workflow)
        if not nodes:
            return None, ""
        anchor_id = anchor.get("node_id")
        by_id = next((n for n in nodes if str(n.get("id")) == str(anchor_id)), None)
        if by_id and (include_bypassed or not self._node_is_bypassed(by_id)):
            return by_id, "id"
        node_type = anchor.get("node_type")
        node_title = anchor.get("node_title")
        candidates = []
        for n in nodes:
            if not include_bypassed and self._node_is_bypassed(n):
                continue
            if node_type and n.get("type") != node_type:
                continue
            if node_title and self._node_title(n) != node_title:
                continue
            candidates.append(n)
        if len(candidates) == 1:
            return candidates[0], "type"
        return None, ""

    def find_node_anchor_values(self) -> None:
        if not self._ensure_selection():
            return
        if not self.node_anchor:
            QMessageBox.information(self, "Anchor by Node", "Set an anchor first.")
            return
        include_bypassed = self.include_bypassed_check.isChecked()
        anchor = self.node_anchor
        field_index = anchor.get("field_index")
        if not isinstance(field_index, int):
            QMessageBox.information(self, "Anchor by Node", "Anchor field index is invalid.")
            return

        self.anchor_results.clear()
        matched = 0
        missing = 0
        for name in self._selected_names():
            workflow = self.workflow_obj_by_name.get(name)
            if not workflow:
                missing += 1
                continue
            node, match_mode = self._find_node_for_anchor(workflow, anchor, include_bypassed=include_bypassed)
            if not node:
                continue
            widgets = node.get("widgets_values")
            if not isinstance(widgets, list) or not (0 <= field_index < len(widgets)):
                continue
            value = widgets[field_index]
            item = QListWidgetItem(f"{name}: {self._format_field_value(value)}")
            item.setData(Qt.UserRole, {"name": name, "value": value, "match": match_mode})
            self.anchor_results.addItem(item)
            matched += 1

        summary = f"Anchor: node {anchor.get('node_id')} / {anchor.get('field_name')} (matches: {matched})"
        if missing:
            summary += f", missing workflows: {missing}"
        self.anchor_status_label.setText(summary)

        if matched == 0:
            QMessageBox.information(self, "Anchor by Node", "No values found for this anchor.")

    def remove_metadata(self) -> None:
        if not self._ensure_selection():
            return
        exiftool_path = self._find_exiftool()
        if not exiftool_path:
            QMessageBox.critical(self, "Remove Metadata", "ExifTool not found. Install it or add it to the repo.")
            return

        existing = [p for p in self.selected_images if os.path.exists(p)]
        missing = [p for p in self.selected_images if not os.path.exists(p)]
        if not existing:
            QMessageBox.warning(self, "Remove Metadata", "Selected files were not found.")
            return

        confirm = QMessageBox.question(
            self,
            "Remove Metadata",
            f"Remove metadata from {len(existing)} image(s)? This modifies the files on disk.",
        )
        if confirm != QMessageBox.Yes:
            return

        args = [str(exiftool_path), "-all="]
        if not self.keep_backup_check.isChecked():
            args.append("-overwrite_original")
        args.extend(existing)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
            )
        finally:
            QApplication.restoreOverrideCursor()

        if result.returncode != 0:
            details = (result.stderr or result.stdout or "").strip()
            if not details:
                details = "Metadata removal failed."
            QMessageBox.critical(self, "Remove Metadata", details)
            return

        message = f"Metadata removed from {len(existing)} image(s)."
        if missing:
            message += f"\nSkipped {len(missing)} missing file(s)."
        message += "\nRun Refresh Pipeline to reparse metadata."
        QMessageBox.information(self, "Remove Metadata", message)
