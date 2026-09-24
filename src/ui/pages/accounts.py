import os
import pickle
import subprocess
import time
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QMenu,
                             QStackedLayout, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from src.core.database import Database
from src.core.cookie_manager import CookieManager
from src.core.paths import app_dir
from src.ui.components.accounts_table import create_accounts_table, COL_ID, COL_NAME, COL_TAG, COL_VIDEOS
from src.ui.components.common import PageHeader, make_button, make_label, plural
from src.ui.dialogs.add_account import AddAccountDialog
from src.ui.dialogs.styled_dialogs import show_info, show_warning, show_error, show_question, get_text

PROJECT_DIR = app_dir()


class AccountsPage(QWidget):
    go_upload = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
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
        self.btn_tag = make_button("Изменить тег")
        self.btn_tag.clicked.connect(self._set_tag)
        self.btn_delete = make_button("Удалить", "danger")
        self.btn_delete.clicked.connect(self._delete_selected)
        for btn in (self.btn_add, self.btn_tag, self.btn_delete):
            toolbar.addWidget(btn)
        toolbar.addStretch()
        root.addLayout(toolbar)

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
        title = make_label("Аккаунтов пока нет")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note = make_label("Добавьте первый: вход через браузер или по кукам.", "muted")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(title)
        empty_layout.addWidget(note)
        self.stack.addWidget(empty)

        root.addWidget(holder, 1)

    def refresh(self):
        accounts = self.db.get_accounts()
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
                item = QTableWidgetItem(text)
                self.table.setItem(row, col, item)
        self.stack.setCurrentIndex(0 if accounts else 1)
        self.header.set_subtitle(
            plural(len(accounts), "аккаунт", "аккаунта", "аккаунтов") if accounts else "Нет добавленных аккаунтов"
        )
        self.btn_upload.setEnabled(bool(accounts))
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
            self.refresh()

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
        self.refresh()

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
            cookies = [
                {"name": "sessionid", "value": dialog.sessionid, "domain": ".tiktok.com", "path": "/",
                 "secure": True, "httpOnly": True},
                {"name": "tt-target-idc", "value": dialog.dc_id, "domain": ".tiktok.com", "path": "/",
                 "secure": True, "httpOnly": False},
            ]
            self._save_account(dialog.username, dialog.tag, cookies)
        else:
            self._login_account(dialog.username, dialog.tag)

    def _save_account(self, username, tag, session_cookies):
        cookies_dir = PROJECT_DIR / "CookiesDir"
        cookies_dir.mkdir(exist_ok=True)
        cookie_name = f"tiktok_session-{username}.cookie"
        with open(cookies_dir / cookie_name, "wb") as f:
            pickle.dump(session_cookies, f)
        self.db.save_account(username, cookie_name, tag=tag)
        self.refresh()
        show_info(self, "Готово", f"Аккаунт «{username}» добавлен с тегом «{tag}».")

    def _login_account(self, username, tag):
        try:
            import undetected_chromedriver as uc

            show_info(self, "Вход в TikTok",
                      f"Сейчас откроется браузер. Войдите в аккаунт «{username}», окно закроется само.")

            def chrome_version():
                for binary in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
                    try:
                        out = subprocess.check_output([binary, "--version"], stderr=subprocess.DEVNULL).decode()
                        return int(out.strip().split()[-1].split(".")[0])
                    except (FileNotFoundError, ValueError, IndexError):
                        continue
                return 0

            options = uc.ChromeOptions()
            proxy = os.environ.get("TIKTOK_PROXY")
            if proxy:
                options.add_argument("--proxy-server={}".format(proxy.replace("socks5h://", "socks5://")))
            version = chrome_version()
            driver = uc.Chrome(options=options, version_main=version) if version > 0 else uc.Chrome(options=options)
            driver.get("https://www.tiktok.com/login")

            collected = {}
            started = time.time()
            while True:
                if time.time() - started > 300:
                    driver.quit()
                    raise TimeoutError("Превышено время ожидания")
                try:
                    for cookie in driver.get_cookies():
                        if cookie["name"] in ("sessionid", "tt-target-idc"):
                            collected[cookie["name"]] = cookie
                    if "sessionid" in collected and "tt-target-idc" in collected:
                        break
                except Exception:
                    driver.quit()
                    raise Exception("Браузер закрыт")
                time.sleep(1)

            driver.quit()
            self._save_account(username, tag, [collected["sessionid"], collected["tt-target-idc"]])
        except Exception as e:
            message = str(e)
            if "закрыт" in message.lower() or "closed" in message.lower():
                show_warning(self, "Вход отменён", "Браузер был закрыт до завершения входа.")
            else:
                show_error(self, "Ошибка входа", message)
