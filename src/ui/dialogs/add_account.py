from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QWidget)
from src.ui.components.common import make_button, make_label
from src.ui.dialogs.styled_dialogs import show_warning


class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить аккаунт")
        self.setMinimumWidth(460)

        self.mode = "login"
        self.username = None
        self.tag = None
        self.sessionid = None
        self.dc_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(6)

        title = make_label("Новый аккаунт")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addSpacing(12)

        layout.addWidget(make_label("Способ входа", "caption"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Через браузер", "login")
        self.mode_combo.addItem("По кукам (sessionid)", "cookies")
        self.mode_combo.currentIndexChanged.connect(self._on_mode)
        layout.addWidget(self.mode_combo)

        self.hint = make_label("", "caption")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        layout.addSpacing(8)

        layout.addWidget(make_label("Имя (только для списка)", "caption"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("например, main")
        layout.addWidget(self.username_input)
        layout.addSpacing(8)

        layout.addWidget(make_label("Тег", "caption"))
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("группа для загрузки")
        layout.addWidget(self.tag_input)

        self.cookie_box = QWidget()
        cookie_layout = QVBoxLayout(self.cookie_box)
        cookie_layout.setContentsMargins(0, 8, 0, 0)
        cookie_layout.setSpacing(6)
        cookie_layout.addWidget(make_label("sessionid", "caption"))
        self.sessionid_input = QLineEdit()
        cookie_layout.addWidget(self.sessionid_input)
        cookie_layout.addSpacing(8)
        cookie_layout.addWidget(make_label("tt-target-idc", "caption"))
        self.dc_input = QLineEdit()
        self.dc_input.setPlaceholderText("например, useast8")
        cookie_layout.addWidget(self.dc_input)
        layout.addWidget(self.cookie_box)

        layout.addSpacing(20)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch()
        cancel = make_button("Отмена")
        cancel.clicked.connect(self.reject)
        self.ok = make_button("Продолжить", "primary")
        self.ok.clicked.connect(self.accept_action)
        self.ok.setDefault(True)
        buttons.addWidget(cancel)
        buttons.addWidget(self.ok)
        layout.addLayout(buttons)

        self._on_mode()

    def _on_mode(self):
        self.mode = self.mode_combo.currentData()
        is_cookies = self.mode == "cookies"
        self.cookie_box.setVisible(is_cookies)
        self.hint.setText(
            "Значения берутся из DevTools браузера: Application, Cookies, tiktok.com."
            if is_cookies else
            "Откроется браузер. Войдите в TikTok, окно закроется само после входа."
        )
        self.ok.setText("Добавить" if is_cookies else "Открыть браузер")
        self.adjustSize()

    def accept_action(self):
        username = self.username_input.text().strip()
        tag = self.tag_input.text().strip()
        if not username or not tag:
            show_warning(self, "Не хватает данных", "Заполните имя и тег.")
            return
        if self.mode == "cookies":
            sessionid = self.sessionid_input.text().strip()
            dc_id = self.dc_input.text().strip()
            if not sessionid or not dc_id:
                show_warning(self, "Не хватает данных", "Укажите sessionid и tt-target-idc.")
                return
            self.sessionid, self.dc_id = sessionid, dc_id
        self.username, self.tag = username, tag
        self.accept()
