from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def set_role(label: QLabel, role: str):
    label.setProperty("role", role)
    repolish(label)


def make_button(text: str, variant: str = "") -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if variant:
        btn.setProperty("variant", variant)
    return btn


def make_label(text: str, role: str = "") -> QLabel:
    label = QLabel(text)
    if role:
        label.setProperty("role", role)
    return label


def make_divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.Shape.HLine)
    return line


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.title = QLabel(title)
        self.title.setObjectName("pageTitle")
        self.subtitle = make_label(subtitle, "muted")

        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)

    def set_subtitle(self, text: str):
        self.subtitle.setText(text)


def plural(n: int, one: str, few: str, many: str) -> str:
    n_abs = abs(n) % 100
    if 11 <= n_abs <= 14:
        form = many
    else:
        last = n_abs % 10
        form = one if last == 1 else few if 2 <= last <= 4 else many
    return f"{n} {form}"
