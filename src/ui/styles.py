BG = "#0e0f11"
SURFACE = "#141518"
SURFACE_2 = "#1a1c20"
BORDER = "#24272c"
BORDER_STRONG = "#353941"
TEXT = "#e8e9eb"
MUTED = "#8a8f98"
FAINT = "#5c6068"
ACCENT = "#6d8dff"
SUCCESS = "#5fbf8a"
DANGER = "#e5686b"

from pathlib import Path

CHEVRON = (Path(__file__).parent / "assets" / "chevron.svg").as_posix()
FONT_FAMILY = '"Segoe UI Variable Text", "Segoe UI", sans-serif'

APP_STYLE = f"""
* {{
    font-family: {FONT_FAMILY};
    font-size: 13px;
    color: {TEXT};
    outline: 0;
}}

QMainWindow, QDialog, QMessageBox, QInputDialog, QWidget#content {{
    background: {BG};
}}

QLabel {{ background: transparent; }}
QLabel#pageTitle {{ font-size: 22px; font-weight: 600; }}
QLabel[role="muted"] {{ color: {MUTED}; }}
QLabel[role="caption"] {{ color: {MUTED}; font-size: 12px; }}
QLabel[role="ok"] {{ color: {SUCCESS}; }}
QLabel[role="err"] {{ color: {DANGER}; }}
QLabel#brand {{ font-size: 14px; font-weight: 600; }}
QLabel#statValue {{ font-size: 24px; font-weight: 600; }}

QFrame#divider {{ background: {BORDER}; border: none; max-height: 1px; min-height: 1px; }}

QWidget#sidebar {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}

QPushButton {{
    background: transparent;
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 0 16px;
    min-height: 34px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {SURFACE_2}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {FAINT}; border-color: {BORDER}; background: transparent; }}

QPushButton[variant="primary"] {{
    background: {TEXT};
    color: {BG};
    border: 1px solid {TEXT};
    font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{ background: #ffffff; border-color: #ffffff; }}
QPushButton[variant="primary"]:pressed {{ background: #cfd1d6; }}
QPushButton[variant="primary"]:disabled {{ background: {BORDER}; color: {FAINT}; border-color: {BORDER}; }}

QPushButton[variant="danger"] {{ color: {DANGER}; }}
QPushButton[variant="danger"]:hover {{ border-color: {DANGER}; background: transparent; }}
QPushButton[variant="danger"]:disabled {{ color: {FAINT}; }}

QPushButton#nav {{
    text-align: left;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0;
    padding: 0 20px;
    min-height: 38px;
    color: {MUTED};
}}
QPushButton#nav:hover {{ color: {TEXT}; background: {SURFACE_2}; }}
QPushButton#nav[active="true"] {{
    color: {TEXT};
    background: {SURFACE_2};
    border-left: 2px solid {ACCENT};
    font-weight: 600;
}}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: {BG};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover {{ border-color: {BORDER_STRONG}; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled {{ color: {FAINT}; }}
QPlainTextEdit#log {{
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 12px;
    color: {MUTED};
}}

QComboBox {{ padding: 0 12px; min-height: 34px; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{
    image: url({CHEVRON});
    width: 12px;
    height: 12px;
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE_2};
    border: 1px solid {BORDER_STRONG};
    padding: 4px;
    selection-background-color: {BORDER};
    selection-color: {TEXT};
}}

QTableWidget {{
    background: transparent;
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: transparent;
    selection-background-color: {SURFACE_2};
    selection-color: {TEXT};
}}
QTableWidget::item {{
    padding: 0 16px;
    border-bottom: 1px solid {BORDER};
}}
QTableWidget::item:selected {{ background: {SURFACE_2}; color: {TEXT}; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: transparent;
    color: {MUTED};
    padding: 10px 16px;
    border: none;
    border-bottom: 1px solid {BORDER};
    font-size: 12px;
    font-weight: 500;
    text-align: left;
}}
QTableCornerButton::section {{ background: transparent; border: none; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER_STRONG}; border-radius: 3px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: {FAINT}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER_STRONG}; border-radius: 3px; min-width: 32px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QMenu {{
    background: {SURFACE_2};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{ padding: 8px 24px 8px 16px; border-radius: 4px; }}
QMenu::item:selected {{ background: {BORDER}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

QToolTip {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    padding: 4px 8px;
}}

QProgressBar {{ background: {BORDER}; border: none; border-radius: 1px; max-height: 2px; min-height: 2px; }}
QProgressBar::chunk {{ background: {TEXT}; }}

QMessageBox QLabel {{ min-width: 280px; }}
QMessageBox QPushButton, QInputDialog QPushButton {{ min-width: 84px; }}
"""
