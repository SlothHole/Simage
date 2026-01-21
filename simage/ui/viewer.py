from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QToolButton, QVBoxLayout, QWidget


class ViewerTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        label = QLabel("Info: Viewer tools are not available yet. More functions will be added later.")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(label)
        help_btn = QToolButton()
        help_btn.setText("?")
        help_btn.setAutoRaise(True)
        help_btn.setToolTip("Viewer tools are planned for a future update.")
        help_btn.setCursor(Qt.WhatsThisCursor)
        help_btn.setFixedSize(16, 16)
        row.addWidget(help_btn)
        row.addStretch(1)
        layout.addLayout(row)
