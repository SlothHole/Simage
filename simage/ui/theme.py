from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

from simage.utils.paths import resolve_repo_path

DEFAULT_THEME = "Soft Light"
DEFAULT_THUMB_SIZE = 128
DEFAULT_THUMB_SPACING = 4
MIN_THUMB_SIZE = 64
MAX_THUMB_SIZE = 256
MIN_THUMB_SPACING = 0
MAX_THUMB_SPACING = 24

THEMES = {
    "Soft Light": {
        "palette": {
            "window": "#f6f2ec",
            "window_text": "#1f1f1f",
            "base": "#ffffff",
            "alternate_base": "#f0e9e0",
            "label_bg": "#efe5da",
            "panel_bg": "#f2e8dc",
            "text": "#1f1f1f",
            "button": "#e8e0d6",
            "button_text": "#1f1f1f",
            "highlight": "#2a6f8f",
            "highlighted_text": "#ffffff",
            "link": "#1f6f8c",
            "placeholder": "#6f6a63",
            "tool_tip_base": "#fff7ed",
            "tool_tip_text": "#1f1f1f",
            "border": "#c9c1b6",
            "button_hover": "#efe7de",
            "button_pressed": "#dacfbf",
            "tab_inactive": "#eae2d8",
            "tab_active": "#ffffff",
            "scrollbar": "#e2d9ce",
            "scrollbar_handle": "#b7a996",
            "scrollbar_handle_hover": "#a79783",
        },
        "thumb": {
            "bg": "#e8e1d8",
            "border": "#b9b2a8",
            "selected_bg": "#d8e7ee",
            "selected_border": "#2a6f8f",
            "text": "#4f4b46",
        },
    },
    "Warm Sand": {
        "palette": {
            "window": "#f3eadf",
            "window_text": "#24201b",
            "base": "#fffaf2",
            "alternate_base": "#efe3d4",
            "label_bg": "#e4d6c5",
            "panel_bg": "#efe2d1",
            "text": "#24201b",
            "button": "#e7d7c4",
            "button_text": "#24201b",
            "highlight": "#b5632a",
            "highlighted_text": "#ffffff",
            "link": "#a15624",
            "placeholder": "#7b7368",
            "tool_tip_base": "#fff3e4",
            "tool_tip_text": "#24201b",
            "border": "#ccb9a5",
            "button_hover": "#efe1d2",
            "button_pressed": "#dbc9b4",
            "tab_inactive": "#eadbca",
            "tab_active": "#fffaf2",
            "scrollbar": "#e1d2c1",
            "scrollbar_handle": "#bfa892",
            "scrollbar_handle_hover": "#ad9884",
        },
        "thumb": {
            "bg": "#ece1d3",
            "border": "#bca892",
            "selected_bg": "#f0dfd0",
            "selected_border": "#b5632a",
            "text": "#4f453a",
        },
    },
    "Coastal Blue": {
        "palette": {
            "window": "#e8f1f5",
            "window_text": "#1a2b33",
            "base": "#f7fbfd",
            "alternate_base": "#dce8ef",
            "label_bg": "#cfe0ea",
            "panel_bg": "#e1ecf2",
            "text": "#1a2b33",
            "button": "#d6e4ec",
            "button_text": "#1a2b33",
            "highlight": "#2b6f7f",
            "highlighted_text": "#ffffff",
            "link": "#2a6d88",
            "placeholder": "#63727a",
            "tool_tip_base": "#eff7fb",
            "tool_tip_text": "#1a2b33",
            "border": "#b4c6d0",
            "button_hover": "#e0ecf2",
            "button_pressed": "#c7d8e2",
            "tab_inactive": "#dce8ef",
            "tab_active": "#f7fbfd",
            "scrollbar": "#d2e1ea",
            "scrollbar_handle": "#9bb3bf",
            "scrollbar_handle_hover": "#8aa2ae",
        },
        "thumb": {
            "bg": "#d7e3ea",
            "border": "#9bb0bb",
            "selected_bg": "#d4e7ed",
            "selected_border": "#2b6f7f",
            "text": "#3d4b52",
        },
    },
    "Forest Moss": {
        "palette": {
            "window": "#e8efe7",
            "window_text": "#1e2a1f",
            "base": "#f6faf5",
            "alternate_base": "#dde6db",
            "label_bg": "#d1dbcf",
            "panel_bg": "#e0e7dd",
            "text": "#1e2a1f",
            "button": "#d7e0d5",
            "button_text": "#1e2a1f",
            "highlight": "#3f6f4a",
            "highlighted_text": "#ffffff",
            "link": "#3a6a46",
            "placeholder": "#6b766c",
            "tool_tip_base": "#eef5ec",
            "tool_tip_text": "#1e2a1f",
            "border": "#b8c5b5",
            "button_hover": "#e0e9dd",
            "button_pressed": "#c7d3c5",
            "tab_inactive": "#dce6da",
            "tab_active": "#f6faf5",
            "scrollbar": "#d2dcd0",
            "scrollbar_handle": "#9fb1a0",
            "scrollbar_handle_hover": "#8fa291",
        },
        "thumb": {
            "bg": "#dde6db",
            "border": "#a9b8a7",
            "selected_bg": "#d8e6d8",
            "selected_border": "#3f6f4a",
            "text": "#3f4b3f",
        },
    },
    "Slate": {
        "palette": {
            "window": "#2a2f35",
            "window_text": "#e4e7ea",
            "base": "#30363d",
            "alternate_base": "#384049",
            "label_bg": "#3a424b",
            "panel_bg": "#303740",
            "text": "#e4e7ea",
            "button": "#353c45",
            "button_text": "#e4e7ea",
            "highlight": "#6f9aa8",
            "highlighted_text": "#0d1115",
            "link": "#7aa9b8",
            "placeholder": "#9aa0a6",
            "tool_tip_base": "#323840",
            "tool_tip_text": "#e4e7ea",
            "border": "#4a525c",
            "button_hover": "#3f4750",
            "button_pressed": "#313840",
            "tab_inactive": "#323840",
            "tab_active": "#353c45",
            "scrollbar": "#323840",
            "scrollbar_handle": "#56606a",
            "scrollbar_handle_hover": "#646f79",
        },
        "thumb": {
            "bg": "#2f353c",
            "border": "#505862",
            "selected_bg": "#3a424b",
            "selected_border": "#6f9aa8",
            "text": "#c6cbd0",
        },
    },
    "Dim Dark": {
        "palette": {
            "window": "#20252b",
            "window_text": "#e7e4dd",
            "base": "#262c34",
            "alternate_base": "#2e343c",
            "label_bg": "#343b44",
            "panel_bg": "#2a3038",
            "text": "#e7e4dd",
            "button": "#2f363f",
            "button_text": "#e7e4dd",
            "highlight": "#5fb3b3",
            "highlighted_text": "#0b0f14",
            "link": "#78c2dd",
            "placeholder": "#9aa0a6",
            "tool_tip_base": "#2a3038",
            "tool_tip_text": "#e7e4dd",
            "border": "#454c55",
            "button_hover": "#39414b",
            "button_pressed": "#2b323b",
            "tab_inactive": "#2b3239",
            "tab_active": "#2f363f",
            "scrollbar": "#2b3239",
            "scrollbar_handle": "#48515b",
            "scrollbar_handle_hover": "#56606a",
        },
        "thumb": {
            "bg": "#2b3138",
            "border": "#505862",
            "selected_bg": "#334047",
            "selected_border": "#5fb3b3",
            "text": "#c8c3bb",
        },
    },
}

THEMES["Custom"] = {
    "palette": dict(THEMES[DEFAULT_THEME]["palette"]),
    "thumb": dict(THEMES[DEFAULT_THEME]["thumb"]),
}

_ACTIVE_THEME = THEMES[DEFAULT_THEME]
_BASE_FONT: QFont | None = None

DEFAULT_SETTINGS = {
    "theme": DEFAULT_THEME,
    "thumb_size": DEFAULT_THUMB_SIZE,
    "thumb_spacing": DEFAULT_THUMB_SPACING,
    "font_family": "",
    "font_size": 0,
    "custom_theme": {
        "palette": {},
        "thumb": {},
    },
    "splitters": {},
    "windows": {},
}


def theme_names() -> list[str]:
    return list(THEMES.keys())


def _settings_path() -> Path:
    return resolve_repo_path("out/ui_settings.json", must_exist=False, allow_absolute=False)


def load_ui_settings() -> dict:
    path = _settings_path()
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    return _normalize_settings(data)


def save_ui_settings(settings: dict) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=True), encoding="utf-8")


def theme_color(key: str, fallback: str) -> str:
    theme = _ACTIVE_THEME or THEMES[DEFAULT_THEME]
    return theme.get("thumb", {}).get(key) or theme.get("palette", {}).get(key) or fallback


def apply_theme(app: QApplication, theme_name: str | None) -> str:
    app.setStyle("Fusion")
    name = theme_name if theme_name in THEMES else DEFAULT_THEME
    if name == "Custom":
        settings = load_ui_settings()
        theme = _build_custom_theme(settings)
    else:
        theme = THEMES[name]
    pal = theme["palette"]
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(pal["window"]))
    palette.setColor(QPalette.WindowText, QColor(pal["window_text"]))
    palette.setColor(QPalette.Base, QColor(pal["base"]))
    palette.setColor(QPalette.AlternateBase, QColor(pal["alternate_base"]))
    palette.setColor(QPalette.Text, QColor(pal["text"]))
    palette.setColor(QPalette.Button, QColor(pal["button"]))
    palette.setColor(QPalette.ButtonText, QColor(pal["button_text"]))
    palette.setColor(QPalette.Highlight, QColor(pal["highlight"]))
    palette.setColor(QPalette.HighlightedText, QColor(pal["highlighted_text"]))
    palette.setColor(QPalette.ToolTipBase, QColor(pal["tool_tip_base"]))
    palette.setColor(QPalette.ToolTipText, QColor(pal["tool_tip_text"]))
    palette.setColor(QPalette.Link, QColor(pal["link"]))
    palette.setColor(QPalette.PlaceholderText, QColor(pal["placeholder"]))
    app.setPalette(palette)
    app.setStyleSheet(_build_stylesheet(pal))
    global _ACTIVE_THEME
    _ACTIVE_THEME = theme
    return name


def apply_font(app: QApplication, settings: dict) -> None:
    global _BASE_FONT
    if _BASE_FONT is None:
        _BASE_FONT = app.font()
    family = settings.get("font_family") or ""
    size = int(settings.get("font_size") or 0)
    if not family and size <= 0:
        app.setFont(_BASE_FONT)
        return
    font = QFont(_BASE_FONT)
    if family:
        font.setFamily(family)
    if size > 0:
        font.setPointSize(size)
    app.setFont(font)


def _build_stylesheet(pal: dict) -> str:
    return f"""
QMainWindow, QDialog {{
    background-color: {pal["window"]};
    color: {pal["text"]};
}}
QTabWidget::pane {{
    background-color: {pal["panel_bg"]};
    color: {pal["text"]};
    border: 0px;
    padding: 0px;
}}
QGroupBox {{
    border: 0px;
    border-radius: 6px;
    margin-top: 12px;
    padding: 0px;
    background-color: {pal["panel_bg"]};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    color: {pal["text"]};
    background-color: {pal["panel_bg"]};
    padding: 0 6px;
}}
QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QComboBox, QSpinBox {{
    background-color: {pal["base"]};
    color: {pal["text"]};
    border: 1px solid {pal["border"]};
    border-radius: 4px;
    padding: 4px;
    min-height: 26px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QListWidget:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {pal["highlight"]};
}}
QPushButton {{
    background-color: {pal["button"]};
    color: {pal["button_text"]};
    border: 1px solid {pal["border"]};
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 28px;
    min-width: 90px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {pal["button_hover"]};
}}
QPushButton:pressed {{
    background-color: {pal["button_pressed"]};
}}
QToolButton {{
    color: {pal["link"]};
    padding: 4px 6px;
    min-height: 24px;
}}
QToolButton:hover {{
    background-color: {pal["alternate_base"]};
    border: 1px solid {pal["border"]};
    border-radius: 4px;
}}
QToolButton:pressed {{
    background-color: {pal["highlight"]};
    color: {pal["highlighted_text"]};
}}
QLabel {{
    color: {pal["text"]};
    background-color: {pal["label_bg"]};
    border-left: 3px solid {pal["border"]};
    border-radius: 2px;
    padding: 2px 8px;
}}
QCheckBox, QRadioButton {{
    color: {pal["text"]};
    padding: 2px 4px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 14px;
    height: 14px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {pal["highlight"]};
    border: 1px solid {pal["border"]};
}}
QMenu {{
    background-color: {pal["base"]};
    color: {pal["text"]};
    border: 1px solid {pal["border"]};
}}
QMenu::item {{
    padding: 4px 8px;
}}
QMenu::item:selected {{
    background-color: {pal["highlight"]};
    color: {pal["highlighted_text"]};
}}
QMenu::separator {{
    height: 1px;
    background: {pal["border"]};
    margin: 4px 0px;
}}
QTabBar::tab {{
    background: {pal["tab_inactive"]};
    color: {pal["text"]};
    border: 1px solid {pal["border"]};
    border-bottom: none;
    padding: 8px 14px;
    margin-right: 2px;
}}
QTabBar::tab:hover {{
    background: {pal["alternate_base"]};
}}
QTabBar::tab:selected {{
    background: {pal["tab_active"]};
}}
QTabBar::tab:!selected {{
    background: {pal["tab_inactive"]};
}}
QHeaderView::section {{
    background: {pal["alternate_base"]};
    color: {pal["text"]};
    border: 1px solid {pal["border"]};
    padding: 4px 6px;
}}
QTableWidget, QTableView, QListWidget, QTreeView {{
    background-color: {pal["base"]};
    color: {pal["text"]};
    border: 1px solid {pal["border"]};
    gridline-color: {pal["border"]};
}}
QScrollArea {{
    background-color: {pal["base"]};
    border: 1px solid {pal["border"]};
}}
QComboBox QAbstractItemView {{
    background-color: {pal["base"]};
    color: {pal["text"]};
    border: 1px solid {pal["border"]};
    selection-background-color: {pal["highlight"]};
    selection-color: {pal["highlighted_text"]};
}}
QAbstractItemView::item {{
    padding: 4px 6px;
    border-radius: 4px;
}}
QAbstractItemView::item:hover {{
    background-color: {pal["alternate_base"]};
}}
QAbstractItemView::item:selected {{
    background-color: {pal["highlight"]};
    color: {pal["highlighted_text"]};
}}
QSplitter::handle {{
    background-color: {pal["alternate_base"]};
    border-radius: 2px;
}}
QSplitter::handle:hover {{
    background-color: {pal["highlight"]};
}}
QSplitter::handle:horizontal {{
    width: 6px;
}}
QSplitter::handle:vertical {{
    height: 6px;
}}
QSlider::groove:horizontal {{
    border: 1px solid {pal["border"]};
    height: 6px;
    background: {pal["alternate_base"]};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {pal["highlight"]};
    border: 1px solid {pal["border"]};
    width: 14px;
    margin: -4px 0px;
    border-radius: 7px;
}}
QComboBox {{
    padding: 4px 8px;
    min-height: 28px;
}}
QComboBox::drop-down {{
    border-left: 1px solid {pal["border"]};
    width: 22px;
}}
QScrollBar:vertical {{
    background: {pal["scrollbar"]};
    width: 12px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {pal["scrollbar_handle"]};
    min-height: 20px;
    border-radius: 6px;
}}
QScrollBar::handle:vertical:hover {{
    background: {pal["scrollbar_handle_hover"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QToolTip {{
    background-color: {pal["tool_tip_base"]};
    color: {pal["tool_tip_text"]};
    border: 1px solid {pal["border"]};
}}
"""


def _normalize_settings(data: dict) -> dict:
    settings = dict(DEFAULT_SETTINGS)
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "custom_theme" and isinstance(value, dict):
                custom = dict(DEFAULT_SETTINGS["custom_theme"])
                palette = value.get("palette")
                if isinstance(palette, dict):
                    custom["palette"] = dict(palette)
                thumb = value.get("thumb")
                if isinstance(thumb, dict):
                    custom["thumb"] = dict(thumb)
                settings["custom_theme"] = custom
            elif key == "splitters" and isinstance(value, dict):
                settings["splitters"] = dict(value)
            elif key == "windows" and isinstance(value, dict):
                settings["windows"] = dict(value)
            else:
                settings[key] = value

    theme = settings.get("theme")
    if theme not in THEMES:
        settings["theme"] = DEFAULT_THEME

    settings["thumb_size"] = _clamp_int(settings.get("thumb_size"), DEFAULT_THUMB_SIZE, MIN_THUMB_SIZE, MAX_THUMB_SIZE)
    settings["thumb_spacing"] = _clamp_int(
        settings.get("thumb_spacing"),
        DEFAULT_THUMB_SPACING,
        MIN_THUMB_SPACING,
        MAX_THUMB_SPACING,
    )

    if not isinstance(settings.get("font_family"), str):
        settings["font_family"] = ""
    settings["font_size"] = _clamp_int(settings.get("font_size"), 0, 0, 72)
    if settings["font_size"] == 0:
        settings["font_family"] = settings.get("font_family", "")

    return settings


def _clamp_int(value: object, default: int, min_value: int, max_value: int) -> int:
    try:
        num = int(value)
    except Exception:
        return default
    return max(min_value, min(max_value, num))


def _build_custom_theme(settings: dict) -> dict:
    base = THEMES[DEFAULT_THEME]
    custom = settings.get("custom_theme") or {}
    pal_override = custom.get("palette") or {}
    thumb_override = custom.get("thumb") or {}
    return {
        "palette": {**base["palette"], **pal_override},
        "thumb": {**base["thumb"], **thumb_override},
    }


def custom_theme_from_settings(settings: dict) -> dict:
    return _build_custom_theme(settings)


def load_splitter_sizes(key: str) -> list[int] | None:
    settings = load_ui_settings()
    splitters = settings.get("splitters")
    if not isinstance(splitters, dict):
        return None
    sizes = splitters.get(key)
    if not isinstance(sizes, list) or not sizes:
        return None
    out: list[int] = []
    for size in sizes:
        try:
            out.append(int(size))
        except Exception:
            continue
    return out if out else None


def save_splitter_sizes(key: str, sizes: list[int]) -> None:
    settings = load_ui_settings()
    splitters = settings.get("splitters")
    if not isinstance(splitters, dict):
        splitters = {}
        settings["splitters"] = splitters
    splitters[key] = [int(s) for s in sizes]
    save_ui_settings(settings)


def load_window_geometry(key: str) -> QByteArray | None:
    settings = load_ui_settings()
    windows = settings.get("windows")
    if not isinstance(windows, dict):
        return None
    data = windows.get(key, {}).get("geometry")
    if not isinstance(data, str) or not data:
        return None
    try:
        return QByteArray.fromBase64(data.encode("ascii"))
    except Exception:
        return None


def save_window_geometry(key: str, geometry: QByteArray) -> None:
    settings = load_ui_settings()
    windows = settings.get("windows")
    if not isinstance(windows, dict):
        windows = {}
        settings["windows"] = windows
    encoded = bytes(geometry.toBase64()).decode("ascii")
    entry = windows.get(key) if isinstance(windows.get(key), dict) else {}
    entry["geometry"] = encoded
    windows[key] = entry
    save_ui_settings(settings)
