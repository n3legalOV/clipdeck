from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame

from src.app.services import ClipForgeService
from src.ui.components.common import PageHeader, make_label


class OverviewPage(QWidget):
    def __init__(self, service: ClipForgeService, parent=None):
        super().__init__(parent)
        self.service = service
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 36, 40, 32)
        root.setSpacing(0)
        root.addWidget(PageHeader("Обзор", "Состояние публикаций и аккаунтов ClipForge"))
        root.addSpacing(28)

        self.cards = QHBoxLayout()
        self.cards.setSpacing(12)
        self.account_card, self.account_value = self._card("Аккаунты")
        self.group_card, self.group_value = self._card("Группы")
        self.history_card, self.history_value = self._card("Публикации")
        self.error_card, self.error_value = self._card("Ошибки")
        for card in (self.account_card, self.group_card, self.history_card, self.error_card):
            self.cards.addWidget(card, 1)
        root.addLayout(self.cards)
        root.addSpacing(22)
        self.hint = make_label("", "muted")
        root.addWidget(self.hint)
        root.addStretch()
        self.refresh()

    def _card(self, title):
        card = QFrame()
        card.setObjectName("statCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        layout.addWidget(make_label(title, "caption"))
        value = make_label("0")
        value.setObjectName("statValue")
        layout.addWidget(value)
        return card, value

    def refresh(self):
        groups = self.service.list_account_groups()
        history = self.service.recent_uploads(200)
        account_count = sum(count for _, count in groups)
        errors = sum(item.status != "ok" for item in history)
        self.account_value.setText(str(account_count))
        self.group_value.setText(str(len(groups)))
        self.history_value.setText(str(len(history)))
        self.error_value.setText(str(errors))
        self.hint.setText("Добавьте аккаунты, выберите группу и начните первую публикацию." if not account_count
                          else "ClipForge готов к работе. Откройте «Публикации», чтобы отправить видео.")
