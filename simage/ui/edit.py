import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QHBoxLayout,
    QAbstractItemView,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSplitter,
)

from simage.utils.paths import resolve_repo_path


class EditTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.records_jsonl_path = str(resolve_repo_path("out/records.jsonl", must_exist=False, allow_absolute=False))
        self.selected_images: List[str] = []
        self.workflow_text_by_name: Dict[str, str] = {}
        self.workflow_obj_by_name: Dict[str, object] = {}
        self.last_find_text = ""
        self.last_find_match_case = False
        self.last_find_relax_values = True
        self._suspend_auto_find = False
        self._auto_find_active = False
        self.node_anchor: Optional[Dict[str, object]] = None
        self.active_workflow_name: Optional[str] = None
        self.current_nodes_by_id: Dict[int, Dict[str, object]] = {}
        self.current_widget_idx_map: Dict[str, Dict[str, int]] = {}

        layout = QVBoxLayout(self)

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
        self.selected_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.selected_list.itemSelectionChanged.connect(self._on_selected_item_changed)

        self.node_list = QListWidget()
        self.node_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.node_list.itemSelectionChanged.connect(self._on_node_selected)

        self.field_list = QListWidget()
        self.field_list.setSelectionMode(QAbstractItemView.SingleSelection)

        self.find_results = QListWidget()
        self.find_results.itemSelectionChanged.connect(self._on_result_selected)

        self.anchor_results = QListWidget()
        self.anchor_results.itemSelectionChanged.connect(self._on_anchor_result_selected)

        self.workflow_view = QTextEdit()
        self.workflow_view.setReadOnly(True)
        self.workflow_view.selectionChanged.connect(self._on_workflow_selection_changed)

        main_splitter = QSplitter(Qt.Horizontal)
        left_splitter = QSplitter(Qt.Vertical)

        selected_panel = QWidget()
        selected_layout = QVBoxLayout(selected_panel)
        selected_header = QHBoxLayout()
        selected_header.addWidget(QLabel("Selected Images"))
        self.selected_label = QLabel("Selected: 0")
        selected_header.addWidget(self.selected_label)
        selected_header.addWidget(
            self._help_button("Shows how many images are currently selected.")
        )
        selected_header.addStretch(1)
        selected_layout.addLayout(selected_header)
        selected_layout.addWidget(QLabel("Click an image to load its workflow."))
        selected_layout.addWidget(self.selected_list)

        matches_panel = QWidget()
        matches_layout = QVBoxLayout(matches_panel)
        matches_header = QHBoxLayout()
        matches_header.addWidget(QLabel("Find Text"))
        matches_header.addWidget(
            self._help_button("Select text in Workflow and it will find matches (if enabled).")
        )
        matches_header.addStretch(1)
        matches_layout.addLayout(matches_header)
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

        anchor_panel = QWidget()
        anchor_layout = QVBoxLayout(anchor_panel)
        anchor_header = QHBoxLayout()
        anchor_header.addWidget(QLabel("Anchor by Node"))
        anchor_header.addWidget(
            self._help_button("Pick a node and field from the current workflow.")
        )
        anchor_header.addStretch(1)
        anchor_layout.addLayout(anchor_header)
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

        left_splitter.addWidget(selected_panel)
        left_splitter.addWidget(anchor_panel)
        left_splitter.addWidget(matches_panel)
        left_splitter.setSizes([220, 360, 240])

        workflow_panel = QWidget()
        workflow_layout = QVBoxLayout(workflow_panel)
        workflow_header = QHBoxLayout()
        workflow_header.addWidget(QLabel("Workflow"))
        workflow_header.addWidget(
            self._help_button("Select text here to find matching sections across images.")
        )
        workflow_header.addStretch(1)
        workflow_layout.addLayout(workflow_header)
        workflow_layout.addWidget(self.workflow_view)

        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(workflow_panel)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)
        main_splitter.setSizes([360, 840])
        layout.addWidget(main_splitter)

        file_actions_panel = QWidget()
        file_actions_layout = QVBoxLayout(file_actions_panel)
        file_header = QHBoxLayout()
        file_header.addWidget(QLabel("File Actions"))
        file_header.addWidget(
            self._help_button("Strip embedded metadata so files can be reparsed.")
        )
        file_header.addStretch(1)
        file_actions_layout.addLayout(file_header)

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
        layout.addWidget(file_actions_panel)
        layout.addStretch(1)

    def _help_button(self, text):
        btn = QToolButton()
        btn.setText("?")
        btn.setAutoRaise(True)
        btn.setToolTip(text)
        btn.setCursor(Qt.WhatsThisCursor)
        btn.setFixedSize(16, 16)
        return btn

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
            return
        self._set_workflow_text(text)
        if highlight_span:
            self._highlight_span(highlight_span[0], highlight_span[1])
        else:
            self._highlight_matches(self.last_find_text, self.last_find_match_case, self.last_find_relax_values)
            self._focus_first_match(self.last_find_text, self.last_find_match_case)
        self._refresh_node_list()

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
        fmt.setBackground(QColor("#ffe08a"))
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
        fmt.setBackground(QColor("#ffe08a"))
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
