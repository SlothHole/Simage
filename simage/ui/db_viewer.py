import sqlite3
from pathlib import Path

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
    QCheckBox,
)

from simage.utils.paths import resolve_repo_path


class DatabaseViewerTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.conn = None

        layout = QVBoxLayout(self)

        # Connection row
        conn_row = QHBoxLayout()
        self.db_path = QLineEdit()
        self.db_path.setPlaceholderText("out/images.db")
        self.db_path.setText("out/images.db")
        self.db_path.setReadOnly(True)
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self.connect_db)
        conn_row.addWidget(QLabel("DB:"))
        conn_row.addWidget(self.db_path)
        conn_row.addWidget(connect_btn)
        layout.addLayout(conn_row)

        self.status_label = QLabel("Not connected.")
        layout.addWidget(self.status_label)

        # SQL editor
        self.sql_input = QPlainTextEdit()
        self.sql_input.setPlaceholderText("Write SQL here. Example: SELECT * FROM images LIMIT 50;")
        layout.addWidget(self.sql_input)

        run_row = QHBoxLayout()
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 100000)
        self.limit_spin.setValue(500)
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run_sql)
        run_row.addWidget(QLabel("Max rows:"))
        run_row.addWidget(self.limit_spin)
        run_row.addStretch(1)
        run_row.addWidget(run_btn)
        layout.addLayout(run_row)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(0)
        self.table.setRowCount(0)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

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

        db_path = self._resolve_db_path("out/images.db")
        uri = f"file:{db_path}?mode=ro"
        self.conn = sqlite3.connect(uri, uri=True)

        self.conn.row_factory = sqlite3.Row
        self.status_label.setText(f"Connected: {db_path}")

    def run_sql(self) -> None:
        if self.conn is None:
            self.status_label.setText("Not connected.")
            return

        sql = self.sql_input.toPlainText().strip()
        if not sql:
            self.status_label.setText("SQL is empty.")
            return

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
