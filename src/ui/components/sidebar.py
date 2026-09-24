from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from src.ui.components.common import make_label, make_divider, repolish


class Sidebar(QWidget):
    page_changed = pyqtSignal(int)

    ITEMS = ["Аккаунты", "Загрузка", "Статистика", "Настройки"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(208)
        self.buttons = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 24, 0, 20)
        layout.setSpacing(0)

        brand = make_label("Clipdeck")
        brand.setObjectName("brand")
        brand.setContentsMargins(20, 0, 20, 0)
        tagline = make_label("Публикации и статистика", "caption")
        tagline.setContentsMargins(20, 2, 20, 0)
        layout.addWidget(brand)
        layout.addWidget(tagline)
        layout.addSpacing(24)
        layout.addWidget(make_divider())
        layout.addSpacing(12)

        for index, name in enumerate(self.ITEMS):
            btn = QPushButton(name)
            btn.setObjectName("nav")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("active", index == 0)
            btn.clicked.connect(lambda _=False, i=index: self.select(i))
            self.buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        self.connection = make_label("", "caption")
        self.connection.setContentsMargins(20, 0, 20, 0)
        self.connection.setWordWrap(True)
        layout.addWidget(self.connection)

    def select(self, index: int, emit: bool = True):
        for i, btn in enumerate(self.buttons):
            btn.setProperty("active", i == index)
            repolish(btn)
        if emit:
            self.page_changed.emit(index)

    def set_connection(self, proxy: str):
        self.connection.setText(f"Соединение\n{proxy}" if proxy else "Соединение\nнапрямую или VPN")
