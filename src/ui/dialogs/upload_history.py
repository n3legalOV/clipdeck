import os

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QHeaderView, QLabel)
from PyQt6.QtCore import Qt

from src.app.services import ClipForgeService
from src.ui.components.common import make_button, make_label, set_role
from src.ui.dialogs.styled_dialogs import show_question

COLUMNS = ["Время", "Аккаунт", "Видео", "Итог", "Причина"]


class UploadHistoryDialog(QDialog):
    """Журнал последних публикаций: кто, что и чем закончилось."""

    def __init__(self, parent=None, db=None, limit=200, service=None):
        super().__init__(parent)
        self.service = service or (ClipForgeService(db) if db is not None else ClipForgeService())
        self.db = self.service.db
        self.limit = limit
        self.setWindowTitle("ClipForge · История публикаций")
        self.setMinimumSize(760, 460)
        self._build()
        self.reload()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(12)

        self.title = QLabel("История публикаций")
        self.title.setObjectName("pageTitle")
        root.addWidget(self.title)

        self.hint = make_label("", "muted")
        root.addWidget(self.hint)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        for column, width in ((0, 140), (1, 150), (2, 200), (3, 90)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(column, width)
        root.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_clear = make_button("Очистить историю")
        self.btn_clear.clicked.connect(self._clear)
        self.btn_close = make_button("Закрыть", "primary")
        self.btn_close.clicked.connect(self.accept)
        actions.addWidget(self.btn_clear)
        actions.addStretch()
        actions.addWidget(self.btn_close)
        root.addLayout(actions)

    def reload(self):
        rows = self.service.recent_uploads(self.limit)
        self.table.setRowCount(0)
        ok_count = 0
        for row in rows:
            username = row.username
            video_path = row.video_path
            status = row.status
            error = row.error
            created_at = row.created_at
            index = self.table.rowCount()
            self.table.insertRow(index)
            ok = status == "ok"
            ok_count += 1 if ok else 0
            values = [
                (created_at or "")[:19].replace("T", " "),
                "@" + (username or "") if username else "",
                os.path.basename(video_path) if video_path else "",
                "опубликовано" if ok else "ошибка",
                "" if ok else (error or "неизвестная причина"),
            ]
            for column, text in enumerate(values):
                item = QTableWidgetItem(text)
                if column in (0, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if column == 3:
                    item.setForeground(Qt.GlobalColor.green if ok else Qt.GlobalColor.red)
                self.table.setItem(index, column, item)

        if rows:
            self.hint.setText(f"Последние записи: {len(rows)} · успешно {ok_count} · с ошибкой {len(rows) - ok_count}")
            set_role(self.hint, "muted")
        else:
            self.hint.setText("Пока ничего не публиковалось")
            set_role(self.hint, "muted")
        self.btn_clear.setEnabled(bool(rows))

    def _clear(self):
        if not show_question(self, "Очистить историю", "Удалить все записи журнала публикаций?"):
            return
        self.service.clear_upload_history()
        self.reload()
