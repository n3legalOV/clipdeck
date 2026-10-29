import pickle

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QMenu, QLineEdit,
                             QComboBox, QStackedLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from src.app.services import ClipForgeService
from src.core.cookie_manager import CookieManager
from src.core.paths import app_dir
from src.ui.components.accounts_table import create_accounts_table, COL_ID, COL_NAME, COL_TAG, COL_VIDEOS
from src.ui.components.common import PageHeader, make_button, make_label, plural
from src.ui.dialogs.add_account import AddAccountDialog
from src.ui.dialogs.import_accounts import ImportAccountsDialog
from src.ui.dialogs.login import LoginDialog
from src.ui.dialogs.styled_dialogs import show_info, show_warning, show_error, show_question, get_text

PROJECT_DIR = app_dir()
ALL_TAGS = "__all__"


class AccountsPage(QWidget):
    go_upload = pyqtSignal()
    accounts_changed = pyqtSignal()

    def __init__(self, service=None, parent=None):
        super().__init__(parent)
        self.service = service or ClipForgeService()
        self.db = self.service.db
        self.cookie_manager = CookieManager()
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 36, 40, 32)
        root.setSpacing(24)

        top = QHBoxLayout()
        self.header = PageHeader("Аккаунты")
        top.addWidget(self.header, 1)
        self.btn_upload = make_button("Загрузить видео", "primary")
        self.btn_upload.clicked.connect(self.go_upload.emit)
        top.addWidget(self.btn_upload, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(top)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.btn_add = make_button("Добавить аккаунт")
        self.btn_add.clicked.connect(self._add_account)
        self.btn_import = make_button("Импорт списка")
        self.btn_import.setToolTip("Добавить сразу много аккаунтов: логин, sessionid, tt-target-idc")
        self.btn_import.clicked.connect(self._import_accounts)
        self.btn_tag = make_button("Изменить тег")
        self.btn_tag.clicked.connect(self._set_tag)
        self.btn_delete = make_button("Удалить", "danger")
        self.btn_delete.clicked.connect(self._delete_selected)
        for btn in (self.btn_add, self.btn_import, self.btn_tag, self.btn_delete):
            toolbar.addWidget(btn)
        toolbar.addStretch()
        root.addLayout(toolbar)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по аккаунту")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(260)
        self.search.textChanged.connect(self._apply_filter)
        self.tag_filter = QComboBox()
        self.tag_filter.setMinimumWidth(180)
        self.tag_filter.currentIndexChanged.connect(self._apply_filter)
        filters.addWidget(self.search)
        filters.addWidget(self.tag_filter)
        filters.addStretch()
        root.addLayout(filters)

        holder = QWidget()
        self.stack = QStackedLayout(holder)

        self.table = create_accounts_table()
        self.table.itemSelectionChanged.connect(self._update_actions)
        self.table.itemDoubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.stack.addWidget(self.table)

        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(6)
        self.empty_title = make_label("Аккаунтов пока нет")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_note = make_label("Добавьте первый: вход через браузер или по кукам.", "muted")
        self.empty_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_note)
        self.stack.addWidget(empty)

        root.addWidget(holder, 1)

        self._accounts = []

    def refresh(self):
        self._accounts = self.db.get_accounts()

        current = self.tag_filter.currentData()
        self.tag_filter.blockSignals(True)
        self.tag_filter.clear()
        self.tag_filter.addItem("Все теги", ALL_TAGS)
        for tag in self.db.get_account_tags():
            self.tag_filter.addItem(tag, tag)
        index = self.tag_filter.findData(current) if current else 0
        self.tag_filter.setCurrentIndex(max(index, 0))
        self.tag_filter.blockSignals(False)

        self._apply_filter()

    def _visible_accounts(self):
        query = self.search.text().strip().lower()
        tag = self.tag_filter.currentData() or ALL_TAGS
        result = []
        for account in self._accounts:
            name = (account[1] or "").lower()
            if query and query not in name:
                continue
            if tag != ALL_TAGS and (account[4] or "") != tag:
                continue
            result.append(account)
        return result

    def _apply_filter(self):
        accounts = self._visible_accounts()
        self.table.setRowCount(0)
        for row, account in enumerate(accounts):
            self.table.insertRow(row)
            values = {
                COL_ID: str(account[0]),
                COL_NAME: account[1] or "",
                COL_TAG: account[4] or "",
                COL_VIDEOS: str(account[6] or 0),
            }
            for col, text in values.items():
                self.table.setItem(row, col, QTableWidgetItem(text))

        total = len(self._accounts)
        if not total:
            self.empty_title.setText("Аккаунтов пока нет")
            self.empty_note.setText("Добавьте первый: вход через браузер или по кукам.")
        else:
            self.empty_title.setText("Ничего не найдено")
            self.empty_note.setText("Измените запрос или выберите другой тег.")
        self.stack.setCurrentIndex(0 if accounts else 1)

        if total:
            subtitle = plural(total, "аккаунт", "аккаунта", "аккаунтов")
            if len(accounts) != total:
                subtitle += f" · показано {len(accounts)}"
        else:
            subtitle = "Нет добавленных аккаунтов"
        self.header.set_subtitle(subtitle)
        self.btn_upload.setEnabled(bool(total))
        self._update_actions()

    def _selected_rows(self):
        return sorted({index.row() for index in self.table.selectionModel().selectedRows()})

    def _update_actions(self):
        has_selection = bool(self._selected_rows())
        self.btn_tag.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def _row_info(self, row):
        return int(self.table.item(row, COL_ID).text()), self.table.item(row, COL_NAME).text()

    def _existing_tags_hint(self):
        tags = self.db.get_account_tags()
        return f"Существующие теги: {', '.join(tags)}" if tags else "Тегов пока нет"

    def _set_tag(self):
        rows = self._selected_rows()
        if not rows:
            return
        current = self.table.item(rows[0], COL_TAG).text() if len(rows) == 1 else ""
        tag, ok = get_text(self, "Изменить тег",
                           f"Новый тег для выбранных ({len(rows)}).\n{self._existing_tags_hint()}", current)
        tag = tag.strip()
        if ok and tag:
            self.db.update_account_tags([self._row_info(r)[0] for r in rows], tag)
            self._changed()

    def _delete_selected(self):
        rows = self._selected_rows()
        if not rows:
            return
        names = [self._row_info(r)[1] for r in rows]
        text = f"Удалить аккаунт «{names[0]}»?" if len(rows) == 1 else f"Удалить выбранные аккаунты ({len(rows)})?"
        if not show_question(self, "Удаление", text + "\nСохранённые куки тоже будут удалены."):
            return
        self.db.delete_accounts([self._row_info(r)[0] for r in rows])
        for name in names:
            self.cookie_manager.delete_cookies(name)
        self._changed()

    def _on_double_click(self, item):
        if item.column() == COL_TAG:
            self.table.clearSelection()
            self.table.selectRow(item.row())
            self._set_tag()

    def _show_context_menu(self, position):
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        if row not in self._selected_rows():
            self.table.clearSelection()
            self.table.selectRow(row)
        menu = QMenu(self)
        tag_action = QAction("Изменить тег", self)
        tag_action.triggered.connect(self._set_tag)
        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(tag_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _add_account(self):
        dialog = AddAccountDialog(self)
        if dialog.exec() != AddAccountDialog.DialogCode.Accepted:
            return
        if dialog.mode == "cookies":
            self._save_account(dialog.username, dialog.tag, dialog.sessionid, dialog.dc_id)
        else:
            self._login_account(dialog.username, dialog.tag)

    def _import_accounts(self):
        dialog = ImportAccountsDialog(self, self.db.get_account_tags())
        if dialog.exec() != ImportAccountsDialog.DialogCode.Accepted:
            return
        source = "\n".join(
            f"{account['username']}\t{account['sessionid']}\t{account['dc_id']}"
            for account in dialog.accounts
        )
        summary = self.service.import_accounts(source, default_tag=dialog.tag)
        for account in dialog.accounts:
            canonical = next(
                (row[1] for row in self.db.get_accounts()
                 if row[1] and row[1].casefold() == account["username"].casefold()),
                account["username"],
            )
            self._write_cookie(canonical, account["sessionid"], account["dc_id"])
        self._changed()
        parts = []
        if summary.added:
            parts.append(f"добавлено {summary.added}")
        if summary.updated:
            parts.append(f"обновлено {summary.updated}")
        if summary.invalid_lines:
            parts.append(f"пропущено строк: {len(summary.invalid_lines)}")
        show_info(self, "Импорт завершён",
                  f"Аккаунты в теге «{dialog.tag}»: " + ", ".join(parts or ["ничего не изменилось"]) + ".")

    def _write_cookie(self, username, session_id, dc_id):
        cookies_dir = PROJECT_DIR / "CookiesDir"
        cookies_dir.mkdir(exist_ok=True)
        cookies = [
            {"name": "sessionid", "value": session_id, "domain": ".tiktok.com", "path": "/",
             "secure": True, "httpOnly": True},
            {"name": "tt-target-idc", "value": dc_id, "domain": ".tiktok.com", "path": "/",
             "secure": True, "httpOnly": False},
        ]
        with open(cookies_dir / f"tiktok_session-{username}.cookie", "wb") as f:
            pickle.dump(cookies, f)

    def _save_account(self, username, tag, session_id, dc_id, quiet=False):
        self._write_cookie(username, session_id, dc_id)
        self.db.save_account(username, f"tiktok_session-{username}.cookie", tag=tag)
        if not quiet:
            self._changed()
            show_info(self, "Готово", f"Аккаунт «{username}» добавлен с тегом «{tag}».")

    def _login_account(self, username, tag):
        dialog = LoginDialog(self, username)
        dialog.start()
        result = dialog.exec()
        if result == LoginDialog.DialogCode.Accepted and dialog.cookies:
            sessionid = next((c["value"] for c in dialog.cookies if c["name"] == "sessionid"), "")
            dc_id = next((c["value"] for c in dialog.cookies if c["name"] == "tt-target-idc"), "")
            self._save_account(username, tag, sessionid, dc_id)
        elif dialog.error:
            message = dialog.error
            if "закрыт" in message.lower() or "closed" in message.lower():
                show_warning(self, "Вход отменён", "Браузер был закрыт до завершения входа.")
            else:
                show_error(self, "Ошибка входа", message)
        elif dialog.cancelled_by_user:
            show_info(self, "Вход отменён", f"Аккаунт «{username}» не добавлен.")

    def _changed(self):
        self.refresh()
        self.accounts_changed.emit()
