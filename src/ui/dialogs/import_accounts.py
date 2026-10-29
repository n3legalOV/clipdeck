from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPlainTextEdit

from src.core.account_import import parse_accounts
from src.ui.components.common import make_button, make_label
from src.ui.dialogs.styled_dialogs import show_warning


class ImportAccountsDialog(QDialog):
    """Массовое добавление аккаунтов вставкой строк «логин + sessionid + dc»."""

    def __init__(self, parent=None, tags=None):
        super().__init__(parent)
        self.setWindowTitle("Импорт аккаунтов")
        self.setMinimumWidth(560)
        self.accounts = []
        self.tag = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(6)

        title = make_label("Импорт аккаунтов")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addSpacing(8)

        hint = make_label(
            "По одной строке на аккаунт: логин, sessionid, tt-target-idc. Разделители — табуляция, "
            "запятая, точка с запятой или пробел. Порядок полей любой, логин можно с @. "
            "Строки, скопированные из Excel или таблицы, подходят как есть.", "caption")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addSpacing(10)

        self.text = QPlainTextEdit()
        self.text.setPlaceholderText(
            "main\te5f1a9c0d3b4...\tuseast8\nsecond\ta71b2c3d4e5f...\tuseast5")
        self.text.setFixedHeight(170)
        self.text.textChanged.connect(self._update_count)
        layout.addWidget(self.text)
        layout.addSpacing(10)

        layout.addWidget(make_label("Тег для всех", "caption"))
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("группа для загрузки")
        layout.addWidget(self.tag_input)
        if tags:
            layout.addWidget(make_label("Существующие теги: " + ", ".join(tags), "caption"))

        self.count = make_label("", "caption")
        self.count.setWordWrap(True)
        layout.addSpacing(6)
        layout.addWidget(self.count)

        layout.addSpacing(16)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch()
        cancel = make_button("Отмена")
        cancel.clicked.connect(self.reject)
        self.ok = make_button("Добавить", "primary")
        self.ok.clicked.connect(self.accept_action)
        self.ok.setDefault(True)
        buttons.addWidget(cancel)
        buttons.addWidget(self.ok)
        layout.addLayout(buttons)

        self._update_count()

    def _update_count(self):
        accounts, errors = parse_accounts(self.text.toPlainText())
        self.accounts = accounts
        parts = [f"Распознано: {len(accounts)}"]
        if errors:
            parts.append("не разобраны строки: " + ", ".join(str(n) for n in errors[:10]))
        self.count.setText("   ·   ".join(parts) if self.text.toPlainText().strip() else "")
        self.ok.setEnabled(bool(accounts))

    def accept_action(self):
        accounts, _ = parse_accounts(self.text.toPlainText())
        tag = self.tag_input.text().strip()
        if not accounts:
            show_warning(self, "Нет данных", "Вставьте хотя бы одну строку с sessionid.")
            return
        if not tag:
            show_warning(self, "Нет тега", "Укажите тег: по нему аккаунты выбираются при загрузке.")
            return
        self.accounts = accounts
        self.tag = tag
        self.accept()
