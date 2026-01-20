import sqlite3
from pathlib import Path

import csv

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
    QComboBox,
    QListWidget,
    QMessageBox,
    QSplitter,
    QAbstractItemView,
    QToolButton,
)

from simage.utils.paths import resolve_repo_path


class DatabaseViewerTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.conn = None
        self._last_headers = []

        layout = QVBoxLayout(self)

        # Connection row
        conn_row = QHBoxLayout()
        self.db_path = QLineEdit()
        self.db_path.setPlaceholderText("out/images.db")
        self.db_path.setText("out/images.db")
        self.db_path.setReadOnly(False)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_db)
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self.connect_db)
        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.clicked.connect(self.disconnect_db)
        conn_row.addWidget(QLabel("DB:"))
        conn_row.addWidget(self.db_path)
        conn_row.addWidget(browse_btn)
        conn_row.addWidget(connect_btn)
        conn_row.addWidget(disconnect_btn)
        conn_row.addWidget(
            self._help_button("Select a SQLite database and connect in read-only mode.")
        )
        layout.addLayout(conn_row)

        self.status_label = QLabel("Not connected.")
        layout.addWidget(self.status_label)

        table_row = QHBoxLayout()
        self.table_combo = QComboBox()
        self.table_combo.setMinimumWidth(220)
        refresh_tables_btn = QPushButton("Refresh Tables")
        refresh_tables_btn.clicked.connect(self.refresh_tables)
        load_table_btn = QPushButton("Load Table")
        load_table_btn.clicked.connect(self.load_table)
        describe_btn = QPushButton("Describe Table")
        describe_btn.clicked.connect(self.describe_table)
        count_btn = QPushButton("Row Count")
        count_btn.clicked.connect(self.count_table)
        table_row.addWidget(QLabel("Table:"))
        table_row.addWidget(self.table_combo)
        table_row.addWidget(refresh_tables_btn)
        table_row.addWidget(load_table_btn)
        table_row.addWidget(describe_btn)
        table_row.addWidget(count_btn)
        table_row.addWidget(
            self._help_button(
                "Pick a table, load rows, describe columns, or get a row count."
            )
        )
        table_row.addStretch(1)
        layout.addLayout(table_row)

        # SQL editor
        editor_split = QSplitter(Qt.Horizontal)
        self.sql_input = QPlainTextEdit()
        self.sql_input.setPlaceholderText("Write SQL here. Example: SELECT * FROM images LIMIT 50;")
        sql_panel = QWidget()
        sql_layout = QVBoxLayout(sql_panel)
        sql_header = QHBoxLayout()
        sql_header.addWidget(QLabel("SQL Editor"))
        sql_header.addWidget(
            self._help_button("Write SQL to execute against the connected database.")
        )
        sql_header.addStretch(1)
        sql_layout.addLayout(sql_header)
        sql_layout.addWidget(self.sql_input)
        editor_split.addWidget(sql_panel)

        history_panel = QWidget()
        history_layout = QVBoxLayout(history_panel)
        history_header = QHBoxLayout()
        history_header.addWidget(QLabel("History"))
        history_header.addWidget(
            self._help_button("Recent SQL commands. Double-click to load.")
        )
        history_header.addStretch(1)
        history_layout.addLayout(history_header)
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.load_history_item)
        history_layout.addWidget(self.history_list)
        editor_split.addWidget(history_panel)
        editor_split.setSizes([700, 240])

        run_row = QHBoxLayout()
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 100000)
        self.limit_spin.setValue(500)
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run_sql)
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.export_csv)
        copy_cell_btn = QPushButton("Copy Cells")
        copy_cell_btn.clicked.connect(self.copy_cells)
        copy_row_btn = QPushButton("Copy Rows")
        copy_row_btn.clicked.connect(self.copy_rows)
        clear_btn = QPushButton("Clear Results")
        clear_btn.clicked.connect(self.clear_results)
        run_row.addWidget(QLabel("Max rows:"))
        run_row.addWidget(self.limit_spin)
        run_row.addStretch(1)
        run_row.addWidget(export_btn)
        run_row.addWidget(copy_cell_btn)
        run_row.addWidget(copy_row_btn)
        run_row.addWidget(clear_btn)
        run_row.addWidget(run_btn)
        run_row.addWidget(
            self._help_button(
                "Run the SQL. Export, copy, or clear results as needed."
            )
        )
        layout.addLayout(run_row)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(0)
        self.table.setRowCount(0)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)

        vertical_split = QSplitter(Qt.Vertical)
        vertical_split.addWidget(editor_split)
        results_panel = QWidget()
        results_layout = QVBoxLayout(results_panel)
        results_header = QHBoxLayout()
        results_header.addWidget(QLabel("Results"))
        results_header.addWidget(
            self._help_button("Query results. Click headers to sort.")
        )
        results_header.addStretch(1)
        results_layout.addLayout(results_header)
        results_layout.addWidget(self.table)
        vertical_split.addWidget(results_panel)
        vertical_split.setSizes([240, 520])
        layout.addWidget(vertical_split)

    def _help_button(self, text: str) -> QToolButton:
        btn = QToolButton()
        btn.setText("?")
        btn.setAutoRaise(True)
        btn.setToolTip(text)
        btn.setCursor(Qt.WhatsThisCursor)
        btn.setFixedSize(16, 16)
        return btn

    def _resolve_db_path(self, path_str: str) -> str:
        raw = Path(path_str)
        if raw.is_absolute():
            return str(raw)
        return str(resolve_repo_path(path_str, must_exist=False, allow_absolute=False))

    def connect_db(self) -> None:
        path = self.db_path.text().strip()
        if not path:
            self.status_label.setText("Missing DB path.")
            return

        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

        db_path = self._resolve_db_path(path)
        uri = f"file:{db_path}?mode=ro"
        self.conn = sqlite3.connect(uri, uri=True)

        self.conn.row_factory = sqlite3.Row
        self.status_label.setText(f"Connected: {db_path}")
        self.refresh_tables()

    def disconnect_db(self) -> None:
        if self.conn is None:
            self.status_label.setText("Not connected.")
            return
        try:
            self.conn.close()
        except Exception:
            pass
        self.conn = None
        self.table_combo.clear()
        self.status_label.setText("Disconnected.")

    def browse_db(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select SQLite DB", "", "SQLite DB (*.db *.sqlite *.sqlite3)")
        if not path:
            return
        self.db_path.setText(path)

    def refresh_tables(self) -> None:
        if self.conn is None:
            self.status_label.setText("Not connected.")
            return
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name;")
            tables = [r[0] for r in cur.fetchall()]
            self.table_combo.clear()
            self.table_combo.addItems(tables)
            self.status_label.setText(f"Tables: {len(tables)}")
        except Exception as exc:
            self.status_label.setText(f"Error: {exc}")

    def _selected_table(self) -> str:
        return self.table_combo.currentText().strip()

    def load_table(self) -> None:
        table = self._selected_table()
        if not table:
            self.status_label.setText("No table selected.")
            return
        limit = self.limit_spin.value()
        limit_clause = f" LIMIT {limit}" if limit else ""
        self.sql_input.setPlainText(f'SELECT * FROM "{table}"{limit_clause};')
        self.run_sql()

    def describe_table(self) -> None:
        table = self._selected_table()
        if not table:
            self.status_label.setText("No table selected.")
            return
        self.sql_input.setPlainText(f'PRAGMA table_info("{table}");')
        self.run_sql()

    def count_table(self) -> None:
        table = self._selected_table()
        if not table:
            self.status_label.setText("No table selected.")
            return
        self.sql_input.setPlainText(f'SELECT COUNT(*) AS row_count FROM "{table}";')
        self.run_sql()

    def run_sql(self) -> None:
        if self.conn is None:
            self.status_label.setText("Not connected.")
            return

        sql = self.sql_input.toPlainText().strip()
        if not sql:
            self.status_label.setText("SQL is empty.")
            return
        self._push_history(sql)

        try:
            cur = self.conn.cursor()
            try:
                cur.execute(sql)
            except sqlite3.ProgrammingError:
                cur.executescript(sql)
                self.conn.commit()
                self.status_label.setText("Script executed.")
                self.table.setRowCount(0)
                self.table.setColumnCount(0)
                return

            if cur.description:
                rows = cur.fetchmany(self.limit_spin.value() or 0) if self.limit_spin.value() else cur.fetchall()
                cols = [d[0] for d in cur.description]
                self._last_headers = cols
                self.table.setColumnCount(len(cols))
                self.table.setHorizontalHeaderLabels(cols)
                self.table.setRowCount(len(rows))
                for r_idx, row in enumerate(rows):
                    for c_idx, col in enumerate(cols):
                        val = row[col]
                        item = QTableWidgetItem("" if val is None else str(val))
                        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                        self.table.setItem(r_idx, c_idx, item)
                self.status_label.setText(f"Rows: {len(rows)}")
            else:
                self.conn.commit()
                self.status_label.setText(f"Statement executed. {cur.rowcount} row(s) affected.")
                self.table.setRowCount(0)
                self.table.setColumnCount(0)
        except Exception as exc:
            self.status_label.setText(f"Error: {exc}")

    def _push_history(self, sql: str) -> None:
        sql = sql.strip()
        if not sql:
            return
        for i in range(self.history_list.count()):
            if self.history_list.item(i).text() == sql:
                return
        self.history_list.insertItem(0, sql)
        if self.history_list.count() > 50:
            self.history_list.takeItem(self.history_list.count() - 1)

    def load_history_item(self) -> None:
        item = self.history_list.currentItem()
        if not item:
            return
        self.sql_input.setPlainText(item.text())

    def export_csv(self) -> None:
        if self.table.rowCount() == 0 or self.table.columnCount() == 0:
            QMessageBox.information(self, "Export CSV", "No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "results.csv", "CSV Files (*.csv)")
        if not path:
            return
        headers = self._last_headers or [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in range(self.table.rowCount()):
                    writer.writerow(
                        [self.table.item(row, col).text() if self.table.item(row, col) else "" for col in range(self.table.columnCount())]
                    )
            QMessageBox.information(self, "Export CSV", f"Saved {self.table.rowCount()} row(s).")
        except Exception as exc:
            QMessageBox.critical(self, "Export CSV", f"Failed to save CSV: {exc}")

    def copy_cells(self) -> None:
        indexes = self.table.selectedIndexes()
        if not indexes:
            return
        indexes = sorted(indexes, key=lambda idx: (idx.row(), idx.column()))
        rows = {}
        for idx in indexes:
            rows.setdefault(idx.row(), {})[idx.column()] = self.table.item(idx.row(), idx.column()).text() if self.table.item(idx.row(), idx.column()) else ""
        lines = []
        for row in sorted(rows.keys()):
            cols = rows[row]
            line = "\t".join(cols.get(c, "") for c in sorted(cols.keys()))
            lines.append(line)
        QApplication.clipboard().setText("\n".join(lines))

    def copy_rows(self) -> None:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if not rows:
            return
        lines = []
        for row in rows:
            lines.append(
                "\t".join(
                    self.table.item(row, col).text() if self.table.item(row, col) else ""
                    for col in range(self.table.columnCount())
                )
            )
        QApplication.clipboard().setText("\n".join(lines))

    def clear_results(self) -> None:
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self._last_headers = []
        self.status_label.setText("Results cleared.")
